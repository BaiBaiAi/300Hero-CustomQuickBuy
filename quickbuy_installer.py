"""Small Windows UI for the bundled quick-buy installer."""
from __future__ import annotations

import hashlib
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox

import bootstrap
import install


def main() -> None:
    root = tk.Tk()
    root.title("300Hero 自定义快捷购买安装器")
    root.resizable(False, False)
    root.geometry("530x175")

    folder = tk.StringVar(value=r"F:\JumpGame\300Hero")
    tk.Label(root, text="游戏目录（包含 Data*.jmp）").pack(anchor="w", padx=15, pady=(15, 4))
    path_row = tk.Frame(root)
    path_row.pack(fill="x", padx=15)
    tk.Entry(path_row, textvariable=folder).pack(side="left", fill="x", expand=True)

    def browse() -> None:
        selected = filedialog.askdirectory(initialdir=folder.get())
        if selected:
            folder.set(selected)

    tk.Button(path_row, text="浏览", command=browse).pack(side="left", padx=(8, 0))
    result = tk.StringVar(value="选择游戏目录后点击“安装并验证”。")
    tk.Label(root, textvariable=result, anchor="w", wraplength=500).pack(fill="x", padx=15, pady=10)

    def game_dir() -> Path:
        path = Path(folder.get()).expanduser().resolve()
        if not path.is_dir():
            raise ValueError(f"游戏目录不存在：{path}")
        return path

    def status() -> None:
        try:
            resource = bootstrap.locate(game_dir())
            source = bootstrap.read_resource(resource)
            state = "已安装" if bootstrap.MARKER in source else "未安装"
            result.set(f"{resource.pack.name} #{resource.index}：快捷购买引导{state}")
            messagebox.showinfo("引导状态", f"{result.get()}\nMD5: {hashlib.md5(source).hexdigest()}")
        except (OSError, ValueError, bootstrap.BootstrapError) as exc:
            messagebox.showerror("检查失败", str(exc))

    def deploy() -> None:
        try:
            target = game_dir()
            install.deploy(target)
            result.set("安装完成。现在可启动游戏，在对局中打开商城测试。")
            messagebox.showinfo("安装完成", f"已安装到：{target}\n请启动游戏进入对局测试。")
        except (OSError, ValueError, bootstrap.BootstrapError) as exc:
            result.set("安装失败，游戏目录未完成更新。")
            messagebox.showerror("安装失败", str(exc))

    actions = tk.Frame(root)
    actions.pack(pady=4)
    tk.Button(actions, text="查看状态", width=15, command=status).pack(side="left", padx=6)
    tk.Button(actions, text="安装并验证", width=15, command=deploy).pack(side="left", padx=6)
    root.mainloop()


if __name__ == "__main__":
    main()
