from __future__ import annotations

import hashlib
from pathlib import Path
from ui_desktop import bind_shortcuts, restore_window_state, save_window_state
from math import floor, ceil
from tkinter import BOTH, END, LEFT, Button, Canvas, Checkbutton, Entry, Frame, IntVar, Label, Listbox, StringVar, Tk, filedialog, messagebox

from PIL import Image, ImageDraw, ImageOps, ImageTk

SUPPORTED = {".jpg", ".jpeg", ".png", ".webp", ".bmp", ".tif", ".tiff"}


def same_path(a: Path, b: Path) -> bool:
    try:
        return a.resolve() == b.resolve()
    except OSError:
        return a.absolute() == b.absolute()


def image_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def ensure_supported(path: Path) -> None:
    if path.suffix.lower() not in SUPPORTED:
        raise ValueError(f"Unsupported image: {path.name}")


def parse_rectangles(text: str) -> list[tuple[int, int, int, int]]:
    rects = []
    if not text.strip():
        return rects
    for chunk in text.split(";"):
        parts = [p.strip() for p in chunk.split(",")]
        if len(parts) != 4:
            raise ValueError("Redaction rectangles must be x,y,width,height separated by ';'.")
        x, y, w, h = map(int, parts)
        if min(x, y, w, h) < 0 or w == 0 or h == 0:
            raise ValueError("Rectangle values must be non-negative and width/height > 0.")
        rects.append((x, y, x + w, y + h))
    return rects


def scale_preview_rectangle(start, end, preview_size, image_size):
    """Map a mouse drag on the EXIF-oriented preview to source-image pixels."""
    pw, ph = preview_size
    iw, ih = image_size
    if min(pw, ph, iw, ih) <= 0:
        raise ValueError("Invalid preview dimensions.")
    x0, x1 = sorted((max(0, min(start[0], pw)), max(0, min(end[0], pw))))
    y0, y1 = sorted((max(0, min(start[1], ph)), max(0, min(end[1], ph))))
    if x0 == x1 or y0 == y1:
        raise ValueError("Drag an area with nonzero width and height.")
    return (floor(x0 * iw / pw), floor(y0 * ih / ph),
            ceil(x1 * iw / pw), ceil(y1 * ih / ph))


def inspect_image(path: Path) -> dict:
    ensure_supported(path)
    with Image.open(path) as probe:
        probe.verify()
    with Image.open(path) as im:
        im.load()
        exif = im.getexif()
        gps = bool(exif and 34853 in exif)
        return {
            "format": im.format,
            "size": im.size,
            "mode": im.mode,
            "exif_tags": len(exif) if exif else 0,
            "gps": gps,
            "icc": "icc_profile" in im.info,
        }


def save_new_image(image: Image.Image, path: Path, format_name: str, **options) -> None:
    """Create a new output exclusively; never replace an earlier export."""
    created = False
    try:
        with path.open("xb") as output:
            created = True
            image.save(output, format=format_name, **options)
    except BaseException:
        if created:
            path.unlink(missing_ok=True)
        raise


def verify_clean_image(path: Path) -> None:
    """Post-export metadata check. Remove only newly created output if it fails."""
    try:
        result = inspect_image(path)
        if result['gps'] or result['icc']:
            raise ValueError('Residual GPS or ICC metadata detected in processed image')
        if path.suffix.lower() not in {'.tif', '.tiff'} and result['exif_tags']:
            raise ValueError('Residual EXIF tags detected in processed image')
    except Exception:
        path.unlink(missing_ok=True)
        raise


def verify_redactions(path: Path, rects: list[tuple[int, int, int, int]]) -> None:
    """Fail closed if a saved lossless output contains pixels in a blacked region."""
    if not rects:
        return
    try:
        with Image.open(path) as result:
            pixels = result.convert("RGB")
            for box in rects:
                if pixels.crop(box).getbbox() is not None:
                    raise ValueError("Exported redaction area contains non-black pixels")
    except Exception:
        path.unlink(missing_ok=True)
        raise


def clean_image(path: Path, output_dir: Path, rects: list[tuple[int, int, int, int]], flatten_png: bool) -> Path:
    ensure_supported(path)
    if path.is_symlink() or not path.is_file():
        raise ValueError("Select a regular image file, not a link.")
    original_digest = image_sha256(path)
    output_dir.mkdir(parents=True, exist_ok=True)
    with Image.open(path) as source:
        if getattr(source, 'n_frames', 1) != 1:
            raise ValueError('Multi-frame images require manual review; no export created.')
        source.load()
        im = ImageOps.exif_transpose(source)
        if im.mode not in ("RGB", "RGBA"):
            im = im.convert("RGBA" if "A" in im.mode else "RGB")
        # Lossy JPEG/WEBP can reintroduce visible edge pixels into redacted
        # regions. Require lossless output before claiming black-area removal.
        if rects and not flatten_png and path.suffix.lower() in {".jpg", ".jpeg", ".webp"}:
            raise ValueError("Redactions require lossless PNG output for JPEG/WEBP sources")
        if rects:
            draw = ImageDraw.Draw(im)
            for box in rects:
                x0, y0, x1, y1 = box
                if not (0 <= x0 < x1 <= im.width and 0 <= y0 < y1 <= im.height):
                    raise ValueError('Redaction rectangle extends beyond image or has zero area.')
                draw.rectangle(box, fill=(0, 0, 0, 255) if im.mode == "RGBA" else (0, 0, 0))
        im.info.clear()
        if flatten_png:
            out = output_dir / f"{path.stem}_clean.png"
            if same_path(path, out):
                raise ValueError("Refusing to overwrite the original image.")
            if im.mode == "RGBA":
                background = Image.new("RGB", im.size, "white")
                background.paste(im, mask=im.getchannel("A"))
                im = background
            else:
                im = im.convert("RGB")
            save_new_image(im, out, "PNG", optimize=True)
            verify_clean_image(out)
            verify_redactions(out, rects)
            if image_sha256(path) != original_digest:
                out.unlink(missing_ok=True)
                raise ValueError("Source image changed during export; the generated copy was removed.")
            return out
        ext = path.suffix.lower()
        out = output_dir / f"{path.stem}_clean{ext}"
        if same_path(path, out):
            raise ValueError("Refusing to overwrite the original image.")
        if ext in {".jpg", ".jpeg"}:
            save_new_image(im.convert("RGB"), out, "JPEG", quality=95, optimize=True)
        elif ext == ".webp":
            save_new_image(im, out, "WEBP", quality=95, method=6)
        elif ext == ".png":
            save_new_image(im, out, "PNG", optimize=True)
        elif ext == ".bmp":
            save_new_image(im.convert("RGB"), out, "BMP")
        else:
            save_new_image(im, out, "TIFF", compression="tiff_deflate")
        verify_clean_image(out)
        verify_redactions(out, rects)
        if image_sha256(path) != original_digest:
            out.unlink(missing_ok=True)
            raise ValueError("Source image changed during export; the generated copy was removed.")
        return out


class App:
    def __init__(self, root: Tk):
        self.root = root
        self.root.title("Image Privacy Cleaner — Windows")
        self.root.geometry("940x700")
        self.root.minsize(820, 620)
        restore_window_state(self.root, "ImagePrivacyCleaner", min_width=820, min_height=620)
        self.files: list[Path] = []
        self.rect_text = StringVar()
        self.flatten = IntVar(value=1)
        self.redactions = {}
        self.current_preview = None
        self.preview_photo = None
        self.preview_size = (0, 0)
        self.original_size = (0, 0)
        self.drag_start = None
        self.drag_id = None
        self.last_exports: list[Path] = []
        self.advanced_visible = False

        head = Frame(root, padx=12, pady=12)
        head.pack(fill="x")
        Label(head, text="Image Privacy Cleaner", font=("Segoe UI", 20, "bold")).pack(anchor="w")
        Label(head, text="Strip EXIF/GPS metadata and optionally black-redact regions. Processing stays local.").pack(anchor="w")
        Label(head, text="① Add images  →  ② Inspect metadata  →  ③ Mark redactions if needed  →  ④ Save clean copies", font=("Segoe UI", 10, "bold"), wraplength=860, justify=LEFT).pack(anchor="w", pady=(4, 0))

        controls = Frame(root, padx=12)
        controls.pack(fill="x")
        add_card = Frame(controls, padx=6, pady=4)
        add_card.pack(side=LEFT, fill="x", expand=True)
        self.add_button = Button(add_card, text="1  Add images", width=16, command=self.add_files)
        self.add_button.pack(anchor="w")
        Label(add_card, text="Choose images; the list and preview appear next.", fg="#666666",
              wraplength=220, justify=LEFT).pack(anchor="w", pady=(3, 0))
        inspect_card = Frame(controls, padx=6, pady=4)
        inspect_card.pack(side=LEFT, fill="x", expand=True)
        self.inspect_button = Button(inspect_card, text="2  Inspect", width=16, command=self.inspect)
        self.inspect_button.pack(anchor="w")
        Label(inspect_card, text="Checks EXIF/GPS metadata before export.", fg="#666666",
              wraplength=210, justify=LEFT).pack(anchor="w", pady=(3, 0))
        save_card = Frame(controls, padx=6, pady=4)
        save_card.pack(side=LEFT, fill="x", expand=True)
        self.export_button = Button(save_card, text="3  Save clean copies", width=20, command=self.export)
        self.export_button.pack(anchor="w")
        Label(save_card, text="Keeps originals and creates new cleaned image copies.", fg="#666666",
              wraplength=230, justify=LEFT).pack(anchor="w", pady=(3, 0))
        self.remove_button = Button(root, text="Remove selected from this list", width=26, command=self.remove_selected)
        self.remove_button.pack(anchor="w", padx=18, pady=(2, 0))

        safe_opts = Frame(root, padx=12, pady=6)
        safe_opts.pack(fill="x")
        Checkbutton(safe_opts, text="Output a new lossless PNG (recommended)", variable=self.flatten).pack(anchor="w")
        Button(safe_opts, text="Advanced: apply manual coordinates to ALL images",
               command=self.toggle_advanced).pack(anchor="w")
        self.advanced = Frame(root, padx=12, pady=6)
        Label(self.advanced, text="WARNING: these coordinates will black out the same area of EVERY image. "
              "Leave blank for ordinary per-image mouse selection.").pack(anchor="w")
        Entry(self.advanced, textvariable=self.rect_text).pack(fill="x", pady=(3, 6))

        Label(root, text="Select an image from the list and drag on its preview to mark an area black.").pack(anchor="w", padx=12)
        Button(root, text="Clear regions for selected image", command=self.clear_regions).pack(anchor="w", padx=12)
        self.canvas = Canvas(root, width=860, height=230, bg="#20242b", highlightthickness=0)
        self.canvas.pack(fill="x", padx=12, pady=4)
        self.canvas.bind("<ButtonPress-1>", self.drag_begin)
        self.canvas.bind("<B1-Motion>", self.drag_move)
        self.canvas.bind("<ButtonRelease-1>", self.drag_end)
        self.listbox = Listbox(root, font=("Consolas", 10))
        self.listbox.pack(fill=BOTH, expand=True, padx=12, pady=12)
        self.listbox.bind("<<ListboxSelect>>", self.select_image)
        bind_shortcuts(self.root, {
            "<Control-O>": self.add_files,
            "<F5>": self.inspect,
            "<Control-S>": self.export,
            "<Delete>": self.remove_selected,
        })
        self.root.protocol("WM_DELETE_WINDOW", self._close)
        self._refresh_actions()

    def _refresh_actions(self):
        has_files = bool(self.files)
        has_selection = bool(self.listbox.curselection())
        self.inspect_button.configure(state="normal" if has_files else "disabled")
        self.export_button.configure(state="normal" if has_files else "disabled")
        self.remove_button.configure(state="normal" if has_selection else "disabled")

    def _close(self):
        save_window_state(self.root, "ImagePrivacyCleaner")
        self.root.destroy()

    def remove_selected(self):
        selected = sorted(self.listbox.curselection(), reverse=True)
        if not selected:
            return
        removed = []
        for index in selected:
            if index < len(self.files):
                removed.append(self.files.pop(index))
        for path in removed:
            self.redactions.pop(path, None)
        self.current_preview = None
        self.preview_photo = None
        self.canvas.delete("all")
        self.render_names()
        if self.files:
            self.listbox.selection_set(0)
            self.show_preview(self.files[0])
        self._refresh_actions()

    def toggle_advanced(self):
        self.advanced_visible = not self.advanced_visible
        if self.advanced_visible:
            self.advanced.pack(fill="x", before=self.canvas)
        else:
            self.advanced.pack_forget()

    def add_files(self):
        paths = filedialog.askopenfilenames(title="Select images")
        for p in paths:
            path = Path(p)
            if path.suffix.lower() not in SUPPORTED:
                messagebox.showwarning("Unsupported", f"Unsupported image: {path.name}")
                continue
            if path not in self.files:
                self.files.append(path)
        self.render_names()
        if self.files:
            self.listbox.selection_clear(0, END)
            self.listbox.selection_set(0)
            self.show_preview(self.files[0])
        self._refresh_actions()

    def render_names(self):
        self.listbox.delete(0, END)
        for p in self.files:
            self.listbox.insert(END, p.name)

    def select_image(self, _event):
        selected = self.listbox.curselection()
        if selected and selected[0] < len(self.files):
            self.show_preview(self.files[selected[0]])
        self._refresh_actions()

    def show_preview(self, path):
        self.current_preview = path
        self.canvas.delete("all")
        self.drag_start = None
        self.preview_photo = None
        self.preview_size = (0, 0)
        self.original_size = (0, 0)
        try:
            with Image.open(path) as source:
                source.load()
                image = ImageOps.exif_transpose(source).convert("RGBA")
                self.original_size = image.size
                image.thumbnail((860, 230), Image.Resampling.LANCZOS)
                self.preview_size = image.size
                self.preview_photo = ImageTk.PhotoImage(image)
            self.canvas.create_image(0, 0, image=self.preview_photo, anchor="nw")
            self.draw_regions()
        except Exception as exc:
            self.canvas.create_text(10, 20, anchor="w", fill="white", text=f"Preview unavailable: {exc}")

    def draw_regions(self):
        pw, ph = self.preview_size
        iw, ih = self.original_size
        if min(pw, ph, iw, ih) <= 0 or self.current_preview is None:
            return
        for x0, y0, x1, y1 in self.redactions.get(self.current_preview, []):
            self.canvas.create_rectangle(
                x0 * pw / iw, y0 * ph / ih, x1 * pw / iw, y1 * ph / ih,
                fill="black", stipple="gray50", outline="#ffca3a", width=2, tags="redaction",
            )

    def drag_begin(self, event):
        if self.current_preview is not None and all(self.preview_size):
            self.drag_start = (event.x, event.y)

    def drag_move(self, event):
        if self.drag_start is None:
            return
        if self.drag_id is not None:
            self.canvas.delete(self.drag_id)
        self.drag_id = self.canvas.create_rectangle(
            *self.drag_start, event.x, event.y, outline="#ffca3a", width=2, dash=(4, 2),
        )

    def drag_end(self, event):
        if self.drag_start is None or self.current_preview is None:
            return
        start = self.drag_start
        self.drag_start = None
        if self.drag_id is not None:
            self.canvas.delete(self.drag_id)
            self.drag_id = None
        try:
            rect = scale_preview_rectangle(start, (event.x, event.y), self.preview_size, self.original_size)
        except ValueError:
            return
        self.redactions.setdefault(self.current_preview, []).append(rect)
        self.canvas.delete("redaction")
        self.draw_regions()

    def clear_regions(self):
        if self.current_preview is not None:
            self.redactions.pop(self.current_preview, None)
        self.canvas.delete("redaction")

    def inspect(self):
        self.listbox.delete(0, END)
        for path in self.files:
            try:
                info = inspect_image(path)
                flags = []
                if info["exif_tags"]:
                    flags.append(f"EXIF={info['exif_tags']}")
                if info["gps"]:
                    flags.append("GPS")
                if info["icc"]:
                    flags.append("ICC")
                flag_text = ", ".join(flags) if flags else "no EXIF/GPS/ICC flags"
                self.listbox.insert(END, f"{path.name} | {info['format']} {info['size']} | {flag_text}")
            except Exception as exc:
                self.listbox.insert(END, f"ERROR {path.name}: {exc}")

    def export(self):
        if not self.files:
            messagebox.showinfo("Image Privacy Cleaner", "Add images first.")
            return
        try:
            rects = parse_rectangles(self.rect_text.get())
        except Exception as exc:
            messagebox.showerror("Invalid rectangles", str(exc))
            return
        if rects and len(self.files) > 1 and not messagebox.askyesno(
                "Global redaction affects all images",
                f"Typed redaction rectangles will be applied to ALL {len(self.files)} images. "
                "This can hide different content in other images. Continue?"):
            return
        folder = filedialog.askdirectory(title="Choose output folder")
        if not folder:
            return
        ok, errors = 0, []
        self.last_exports = []
        for path in self.files:
            try:
                output = clean_image(path, Path(folder), rects + self.redactions.get(path, []), bool(self.flatten.get()))
                verified = inspect_image(output)
                if verified["gps"] or verified["icc"] or (output.suffix.lower() not in {".tif", ".tiff"} and verified["exif_tags"]):
                    raise ValueError("Output metadata check failed; do not share the output.")
                self.last_exports.append(output)
                ok += 1
            except Exception as exc:
                errors.append(f"{path.name}: {exc}")
        if errors:
            messagebox.showwarning("Image Privacy Cleaner: partial/failed",
                f"Exported {ok} image(s); {len(errors)} failed. Review output before sharing.\n"
                + "\n".join(errors[:8]))
        else:
            messagebox.showinfo("Image Privacy Cleaner",
                f"Exported {ok} image(s). Open the saved PNG(s) and verify every black area.")


def main():
    from i18n import install_bilingual_ui

    root = Tk()
    App(root)
    install_bilingual_ui(root)
    root.mainloop()


if __name__ == "__main__":
    import sys

    if "--self-test" in sys.argv:
        # Runs the same safe file-processing smoke cases inside the bundled EXE.
        import smoke_test  # noqa: F401
    else:
        main()
