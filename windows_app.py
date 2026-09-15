from __future__ import annotations

from pathlib import Path
from tkinter import BOTH, END, LEFT, Button, Checkbutton, Entry, Frame, IntVar, Label, Listbox, StringVar, Tk, filedialog, messagebox

from PIL import Image, ImageDraw, ImageOps

SUPPORTED = {".jpg", ".jpeg", ".png", ".webp", ".bmp", ".tif", ".tiff"}


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
    with Image.open(path) as im:
        exif = im.getexif()
        gps = False
        if exif:
            gps = 34853 in exif
        return {
            "format": im.format,
            "size": im.size,
            "mode": im.mode,
            "exif_tags": len(exif) if exif else 0,
            "gps": gps,
            "icc": "icc_profile" in im.info,
        }


def clean_image(path: Path, output_dir: Path, rects: list[tuple[int, int, int, int]], flatten_png: bool) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    with Image.open(path) as source:
        im = ImageOps.exif_transpose(source)
        if im.mode not in ("RGB", "RGBA"):
            im = im.convert("RGBA" if "A" in im.mode else "RGB")
        if rects:
            draw = ImageDraw.Draw(im)
            for box in rects:
                draw.rectangle(box, fill=(0, 0, 0, 255) if im.mode == "RGBA" else (0, 0, 0))
        # Pillow carries ICC and other source metadata in Image.info across
        # transformations. Clear it explicitly before every output encoder.
        im.info.clear()
        if flatten_png:
            out = output_dir / f"{path.stem}_clean.png"
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
        if ext in {".jpg", ".jpeg"}:
            im.convert("RGB").save(out, format="JPEG", quality=95, optimize=True)
        elif ext == ".webp":
            im.save(out, format="WEBP", quality=95, method=6)
        elif ext == ".png":
            im.save(out, format="PNG", optimize=True)
        else:
            im.save(out)
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
