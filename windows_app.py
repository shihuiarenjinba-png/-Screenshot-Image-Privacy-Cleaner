from __future__ import annotations

from pathlib import Path
from tkinter import BOTH, END, LEFT, Button, Checkbutton, Entry, Frame, IntVar, Label, Listbox, StringVar, Tk, filedialog, messagebox

from PIL import Image, ImageDraw, ImageOps

SUPPORTED = {".jpg", ".jpeg", ".png", ".webp", ".bmp", ".tif", ".tiff"}

# Structural TIFF fields describe how pixels are encoded. They are required for a
# readable TIFF and are not privacy metadata by themselves. Unknown and content-
# bearing fields remain flagged so the inspection fails toward manual review.
TIFF_STRUCTURAL_TAGS = {
    254, 256, 257, 258, 259, 262, 266, 273, 277, 278, 279,
    282, 283, 284, 286, 287, 292, 293, 296, 317, 320, 322,
    323, 324, 325, 338, 339,
}


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


def inspect_image(path: Path) -> dict:
    ensure_supported(path)
    with Image.open(path) as probe:
        probe.verify()
    with Image.open(path) as im:
        im.load()
        exif = im.getexif()
        gps = bool(exif and 34853 in exif)
        raw_exif_tags = set(exif.keys()) if exif else set()
        structural_tags = raw_exif_tags & TIFF_STRUCTURAL_TAGS if im.format == "TIFF" else set()
        separately_reported_tags = {34675} if "icc_profile" in im.info else set()
        privacy_tags = raw_exif_tags - structural_tags - separately_reported_tags
        return {
            "format": im.format,
            "size": im.size,
            "mode": im.mode,
            "exif_tags": len(privacy_tags),
            "raw_exif_tags": len(raw_exif_tags),
            "structural_tags": len(structural_tags),
            "gps": gps,
            "icc": "icc_profile" in im.info,
        }


def clean_image(path: Path, output_dir: Path, rects: list[tuple[int, int, int, int]], flatten_png: bool) -> Path:
    ensure_supported(path)
    output_dir.mkdir(parents=True, exist_ok=True)
    with Image.open(path) as source:
        source.load()
        im = ImageOps.exif_transpose(source)
        if im.mode not in ("RGB", "RGBA"):
            im = im.convert("RGBA" if "A" in im.mode else "RGB")
        # Rebuild from pixels so no EXIF/TIFF tag object survives the export.
        im = Image.frombytes(im.mode, im.size, im.tobytes())
        if rects:
            draw = ImageDraw.Draw(im)
            for box in rects:
                draw.rectangle(box, fill=(0, 0, 0, 255) if im.mode == "RGBA" else (0, 0, 0))
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
            im.save(out, format="PNG", optimize=True)
            return out
        ext = path.suffix.lower()
        out = output_dir / f"{path.stem}_clean{ext}"
        if same_path(path, out):
            raise ValueError("Refusing to overwrite the original image.")
        if ext in {".jpg", ".jpeg"}:
            im.convert("RGB").save(out, format="JPEG", quality=95, optimize=True)
        elif ext == ".webp":
            im.save(out, format="WEBP", quality=95, method=6)
        elif ext == ".png":
            im.save(out, format="PNG", optimize=True)
        elif ext == ".bmp":
            im.convert("RGB").save(out, format="BMP")
        else:
            im.save(out, format="TIFF", compression="tiff_deflate")
        return out


class App:
    def __init__(self, root: Tk):
        self.root = root
        self.root.title("Image Privacy Cleaner — Windows")
        self.root.geometry("900x600")
        self.files: list[Path] = []
        self.rect_text = StringVar()
        self.flatten = IntVar(value=1)

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
        Label(opts, text="Black-redaction rectangles (x,y,width,height; ...):").pack(anchor="w")
        Entry(opts, textvariable=self.rect_text).pack(fill="x", pady=(3, 6))
        Checkbutton(opts, text="Flatten output to metadata-free PNG", variable=self.flatten).pack(anchor="w")

        self.listbox = Listbox(root, font=("Consolas", 10))
        self.listbox.pack(fill=BOTH, expand=True, padx=12, pady=12)

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

    def render_names(self):
        self.listbox.delete(0, END)
        for p in self.files:
            self.listbox.insert(END, str(p))

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
                clean_image(path, Path(folder), rects, bool(self.flatten.get()))
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
