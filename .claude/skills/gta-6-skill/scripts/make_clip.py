#!/usr/bin/env python3
"""Monte un clip vertical 9:16 (1080x1920, H.264/AAC MP4) à partir d'une source.

Un seul passage continu : --start → --end. Aucune compilation.

Exemples :
  python3 make_clip.py --source vod.mp4 --start 01:23:45 --end 01:24:31 --out clips/x/master.mp4
  python3 make_clip.py --source vod.mp4 --start 5025 --end 5071 --mode crop --crop-x 0.4 \
      --subs clips/x/subs.ass --hook "Il ne s'attendait pas à ça" --out clips/x/master.mp4
"""
from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

W, H = 1080, 1920
SHORTS_MAX_SECONDS = 180


def parse_time(value: str) -> float:
    """Accepte '83.5', '01:23', '01:23:45', '01:23:45.250'."""
    value = value.strip()
    parts = value.split(":")
    try:
        nums = [float(p) for p in parts]
    except ValueError:
        sys.exit(f"Timestamp invalide : {value!r}")
    seconds = 0.0
    for n in nums:
        seconds = seconds * 60 + n
    return seconds


def fmt_time(seconds: float) -> str:
    h = int(seconds // 3600)
    m = int(seconds % 3600 // 60)
    s = seconds % 60
    return f"{h:02d}:{m:02d}:{s:06.3f}"


def ass_escape_path(path: Path) -> str:
    # Échappement pour les filtres ffmpeg (deux-points, apostrophes, backslashes).
    p = str(path.resolve())
    return p.replace("\\", "\\\\").replace(":", "\\:").replace("'", "\\'")


def download_section(url: str, start: float, end: float, workdir: Path) -> Path:
    if not shutil.which("yt-dlp"):
        sys.exit(
            "La source est une URL mais yt-dlp n'est pas installé.\n"
            "Installer : pip install yt-dlp — ou fournir un fichier local."
        )
    out = workdir / "source.%(ext)s"
    # Petite marge pour éviter un premier keyframe manquant.
    pad_start = max(0.0, start - 2)
    cmd = [
        "yt-dlp", "-f", "bv*[height<=1080]+ba/b[height<=1080]/b",
        "--download-sections", f"*{pad_start}-{end + 1}",
        "--force-keyframes-at-cuts", "--merge-output-format", "mp4",
        "-o", str(out), url,
    ]
    print("→", " ".join(cmd))
    subprocess.run(cmd, check=True)
    files = list(workdir.glob("source.*"))
    if not files:
        sys.exit("Téléchargement échoué : aucun fichier produit.")
    return files[0]


def hook_ass(text: str, duration: float, path: Path) -> None:
    """Fichier ASS contenant uniquement le hook écran (haut de l'image, zone sûre)."""
    end = fmt_time(duration)[1:-1]  # H:MM:SS.cc
    text = text.replace("\n", "\\N")
    path.write_text(
        "[Script Info]\nScriptType: v4.00+\nPlayResX: 1080\nPlayResY: 1920\n"
        "WrapStyle: 0\nScaledBorderAndShadow: yes\n\n"
        "[V4+ Styles]\n"
        "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, "
        "BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, "
        "BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding\n"
        "Style: Hook,DejaVu Sans,74,&H00FFFFFF,&H00FFFFFF,&H00000000,&HC0000000,"
        "-1,0,0,0,100,100,0,0,3,18,0,8,90,150,250,1\n\n"
        "[Events]\nFormat: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text\n"
        f"Dialogue: 1,0:00:00.00,{end},Hook,,0,0,0,,{{\\fad(120,200)}}{text}\n",
        encoding="utf-8",
    )


def build_filter(args, hook_file: Path | None) -> str:
    if args.mode == "blur":
        chain = (
            f"[0:v]split=2[bgsrc][fgsrc];"
            f"[bgsrc]scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},"
            f"boxblur=luma_radius=40:luma_power=2,eq=brightness=-0.08[bg];"
            f"[fgsrc]scale={W}:-2[fg];"
            f"[bg][fg]overlay=(W-w)/2:(H-h)/2[base]"
        )
    elif args.mode == "crop":
        x = min(max(args.crop_x, 0.0), 1.0)
        chain = (
            f"[0:v]scale={W}:{H}:force_original_aspect_ratio=increase,"
            f"crop={W}:{H}:(iw-{W})*{x}:(ih-{H})/2[base]"
        )
    elif args.mode == "facecam":
        if not args.cam:
            sys.exit("--mode facecam exige --cam x,y,w,h (pixels de la source).")
        cx, cy, cw, ch = (int(v) for v in args.cam.split(","))
        cam_h = int(H * 0.38) // 2 * 2
        game_h = H - cam_h
        chain = (
            f"[0:v]split=2[c][g];"
            f"[c]crop={cw}:{ch}:{cx}:{cy},scale={W}:{cam_h}:force_original_aspect_ratio=increase,"
            f"crop={W}:{cam_h}[cam];"
            f"[g]scale={W}:{game_h}:force_original_aspect_ratio=increase,crop={W}:{game_h}[game];"
            f"[cam][game]vstack[base]"
        )
    else:  # fit : bandes noires
        chain = (
            f"[0:v]scale={W}:{H}:force_original_aspect_ratio=decrease,"
            f"pad={W}:{H}:(ow-iw)/2:(oh-ih)/2:black[base]"
        )

    last = "base"
    if args.subs:
        chain += f";[{last}]ass='{ass_escape_path(Path(args.subs))}'[subbed]"
        last = "subbed"
    if hook_file:
        chain += f";[{last}]ass='{ass_escape_path(hook_file)}'[hooked]"
        last = "hooked"
    chain += f";[{last}]fps=30,format=yuv420p,setsar=1[vout]"
    return chain


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--source", required=True, help="Fichier vidéo local ou URL (yt-dlp)")
    ap.add_argument("--start", required=True, help="Début (s ou HH:MM:SS)")
    ap.add_argument("--end", required=True, help="Fin (s ou HH:MM:SS)")
    ap.add_argument("--out", required=True, help="Fichier MP4 de sortie")
    ap.add_argument("--mode", choices=["blur", "crop", "facecam", "fit"], default="blur")
    ap.add_argument("--crop-x", type=float, default=0.5, help="Position horizontale du recadrage (0–1)")
    ap.add_argument("--cam", help="Zone facecam dans la source : x,y,w,h")
    ap.add_argument("--subs", help="Fichier .ass (ou .srt) à incruster")
    ap.add_argument("--hook", help="Texte du hook affiché au début")
    ap.add_argument("--hook-duration", type=float, default=2.8)
    ap.add_argument("--crf", type=int, default=20)
    ap.add_argument("--no-loudnorm", action="store_true", help="Ne pas normaliser l'audio")
    ap.add_argument("--cover", type=float, help="Exporter cover.jpg à t secondes (dans le clip)")
    args = ap.parse_args()

    if not shutil.which("ffmpeg"):
        sys.exit("ffmpeg est requis.")

    start, end = parse_time(args.start), parse_time(args.end)
    if end <= start:
        sys.exit("--end doit être après --start.")
    duration = end - start
    if duration > SHORTS_MAX_SECONDS:
        print(f"⚠ Durée {duration:.0f}s > {SHORTS_MAX_SECONDS}s : publiable sur TikTok mais pas en YouTube Short.")
    elif duration < 8:
        print(f"⚠ Durée {duration:.1f}s très courte : vérifier que contexte et payoff sont présents.")

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)

    with tempfile.TemporaryDirectory() as tmp:
        tmpdir = Path(tmp)
        src = args.source
        seek = start
        if src.startswith(("http://", "https://")):
            src_path = download_section(src, start, end, tmpdir)
            seek = min(2.0, start)  # la section commence ~2 s avant start
            src = str(src_path)
        elif not Path(src).exists():
            sys.exit(f"Source introuvable : {src}")

        hook_file = None
        if args.hook:
            hook_file = tmpdir / "hook.ass"
            hook_ass(args.hook, min(args.hook_duration, duration), hook_file)

        cmd = [
            "ffmpeg", "-hide_banner", "-loglevel", "error", "-stats", "-y",
            "-ss", f"{seek:.3f}", "-i", src, "-t", f"{duration:.3f}",
            "-filter_complex", build_filter(args, hook_file),
            "-map", "[vout]", "-map", "0:a:0?",
            "-c:v", "libx264", "-preset", "medium", "-crf", str(args.crf),
            "-profile:v", "high", "-level", "4.2", "-pix_fmt", "yuv420p",
            "-c:a", "aac", "-b:a", "160k", "-ar", "48000", "-ac", "2",
            "-movflags", "+faststart",
        ]
        if not args.no_loudnorm:
            cmd[cmd.index("-c:a"):cmd.index("-c:a")] = ["-af", "loudnorm=I=-14:TP=-1.5:LRA=11"]
        cmd.append(str(out))
        print("→ ffmpeg", f"[{fmt_time(start)} → {fmt_time(end)}, {duration:.1f}s, mode={args.mode}]")
        subprocess.run(cmd, check=True)

    if args.cover is not None:
        cover = out.with_name("cover.jpg")
        subprocess.run(
            ["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-ss", str(args.cover),
             "-i", str(out), "-frames:v", "1", "-q:v", "2", str(cover)],
            check=True,
        )
        print(f"✓ Couverture : {cover}")

    print(f"✓ Clip : {out}  (1080x1920, H.264/AAC, {duration:.1f}s)")


if __name__ == "__main__":
    main()
