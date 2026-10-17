from __future__ import annotations

from pathlib import Path
from math import floor, ceil
from tkinter import BOTH, END, LEFT, Button, Canvas, Checkbutton, Entry, Frame, IntVar, Label, Listbox, StringVar, Tk, filedialog, messagebox

from PIL import Image, ImageDraw, ImageOps, ImageTk

SUPPORTED = {".jpg", ".jpeg", ".png", ".webp", ".bmp", ".tif", ".tiff"}


def same_path(a: Path, b: Path) -> bool:
    try:
        return a.resolve() == b.resolve()
    except OSError:
        return a.absolute() == b.absolute()


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


def clean_image(path: Path, output_dir: Path, rects: list[tuple[int, int, int, int]], flatten_png: bool) -> Path:
    ensure_supported(path)
    output_dir.mkdir(parents=True, exist_ok=True)
    with Image.open(path) as source:
        source.load()
        im = ImageOps.exif_transpose(source)
        if im.mode not in ("RGB", "RGBA"):
            im = im.convert("RGBA" if "A" in im.mode else "RGB")
        if rects:
            draw = ImageDraw.Draw(im)
            for box in rects:
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
            im.save(out, format="PNG", optimize=True)
        elif ext == ".bmp":
            save_new_image(im.convert("RGB"), out, "BMP")
        else:
            save_new_image(im, out, "TIFF", compression="tiff_deflate")
        return out


class App:
    def __init__(self, root: Tk):
        self.root = root
        self.root.title("Image Privacy Cleaner — Windows")
        self.root.geometry("940x790")
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

        head = Frame(root, padx=12, pady=12)
        head.pack(fill="x")
        Label(head, text="Image Privacy Cleaner", font=("Segoe UI", 20, "bold")).pack(anchor="w")
        Label(head, text="Strip EXIF/GPS metadata and optionally black-redact regions. Processing stays local.").pack(anchor="w")

        controls = Frame(root, padx=12)
        controls.pack(fill="x")
        Button(controls, text="Add images", width=16, command=self.add_files).pack(side=LEFT)
        Button(controls, text="Inspect", width=16, command=self.inspect).pack(side=LEFT, padx=8)
        Button(controls, text="Clean & export", width=18, command=self.export).pack(side=LEFT)

        opts = Frame(root, padx=12, pady=10)
        opts.pack(fill="x")
        Label(opts, text="Advanced: manual rectangles apply to all images (x,y,width,height; ...):").pack(anchor="w")
        Entry(opts, textvariable=self.rect_text).pack(fill="x", pady=(3, 6))
        Checkbutton(opts, text="Flatten output to metadata-free PNG", variable=self.flatten).pack(anchor="w")

        Label(root, text="Select an image from the list and drag on its preview to mark an area black.").pack(anchor="w", padx=12)
        Button(root, text="Clear regions for selected image", command=self.clear_regions).pack(anchor="w", padx=12)
        self.canvas = Canvas(root, width=860, height=260, bg="#20242b", highlightthickness=0)
        self.canvas.pack(fill="x", padx=12, pady=4)
        self.canvas.bind("<ButtonPress-1>", self.drag_begin)
        self.canvas.bind("<B1-Motion>", self.drag_move)
        self.canvas.bind("<ButtonRelease-1>", self.drag_end)
        self.listbox = Listbox(root, font=("Consolas", 10))
        self.listbox.pack(fill=BOTH, expand=True, padx=12, pady=12)
        self.listbox.bind("<<ListboxSelect>>", self.select_image)

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
            self.show_preview(self.files[0])

    def render_names(self):
        self.listbox.delete(0, END)
        for p in self.files:
            self.listbox.insert(END, str(p))

    def select_image(self, _event):
        selected = self.listbox.curselection()
        if selected and selected[0] < len(self.files):
            self.show_preview(self.files[selected[0]])

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
                image.thumbnail((860, 260), Image.Resampling.LANCZOS)
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
        folder = filedialog.askdirectory(title="Choose output folder")
        if not folder:
            return
        ok, errors = 0, []
        for path in self.files:
            try:
                output = clean_image(path, Path(folder), rects + self.redactions.get(path, []), bool(self.flatten.get()))
                verified = inspect_image(output)
                if verified["gps"] or verified["icc"] or (output.suffix.lower() not in {".tif", ".tiff"} and verified["exif_tags"]):
                    raise ValueError("Output metadata check failed; do not share the output.")
                ok += 1
            except Exception as exc:
                errors.append(f"{path.name}: {exc}")
        messagebox.showinfo("Image Privacy Cleaner", f"Exported {ok} cleaned image(s)." + ("\n" + "\n".join(errors[:8]) if errors else ""))


def main():
    from i18n import install_bilingual_ui

    root = Tk()
    App(root)
    install_bilingual_ui(root)
    root.mainloop()


if __name__ == "__main__":
    main()
