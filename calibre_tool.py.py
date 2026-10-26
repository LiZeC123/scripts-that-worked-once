#!/usr/bin/env python3
"""
Calibre 书库工具：
1. 导出所有书名
2. 扫描书库，找出不在数据库中的电子书文件
3. 删除这些孤儿电子书（支持预览和确认）

# 先查找并显示孤儿文件，确认后再删除（两步）
python3 calibre_tool.py --library ~/BookLibary --find-orphans
python3 calibre_tool.py --library ~/BookLibary --delete-orphans
"""

import os
import sys
import sqlite3
import argparse
from pathlib import Path

# 常见电子书扩展名（小写）
BOOK_EXTENSIONS = {
    '.epub', '.pdf', '.mobi', '.azw3', '.azw', '.docx', '.txt',
    '.fb2', '.djvu', '.cbz', '.cbr', '.prc', '.pdb', '.lit', '.kepub'
}

def get_full_file_path(library_root: Path, book_path: str, data_name: str, fmt: str) -> Path:
    """
    根据 books.path 和 data.name 生成完整的文件路径
    自动处理 data.name 缺少扩展名的情况
    """
    dir_path = library_root / book_path
    if '.' in data_name:
        filename = data_name
    else:
        filename = f"{data_name}.{fmt.lower()}"
    return dir_path / filename

def load_known_files(db_path: Path, library_root: Path) -> set:
    """从数据库读取所有已知的电子书文件绝对路径"""
    known = set()
    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()
    cursor.execute("""
        SELECT b.path, d.name, d.format
        FROM books b
        JOIN data d ON b.id = d.book
    """)
    for book_path, data_name, fmt in cursor.fetchall():
        if not book_path or not data_name:
            continue
        try:
            full = get_full_file_path(library_root, book_path, data_name, fmt)
            known.add(str(full.resolve()))
        except Exception as e:
            print(f"警告: 解析路径出错 ({book_path}, {data_name}, {fmt}): {e}", file=sys.stderr)
    conn.close()
    return known

def export_book_titles(db_path: Path, output_file: Path = None):
    """功能1: 导出所有书名"""
    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()
    cursor.execute("SELECT title FROM books ORDER BY id")
    titles = [row[0] for row in cursor.fetchall()]
    conn.close()
    if output_file:
        with open(output_file, 'w', encoding='utf-8') as f:
            for title in titles:
                f.write(title + '\n')
        print(f"已导出 {len(titles)} 条书名到 {output_file}")
    else:
        for title in titles:
            print(title)
        print(f"共 {len(titles)} 本书", file=sys.stderr)

def find_orphan_books(library_root: Path, known_files: set) -> list:
    """扫描书库，返回不在数据库中的电子书文件路径列表"""
    orphan_paths = []
    skip_dirs = {'.caltrash', 'Trash', '__MACOSX', '.DS_Store'}
    for root, dirs, files in os.walk(library_root):
        dirs[:] = [d for d in dirs if d not in skip_dirs]
        for file in files:
            file_path = Path(root) / file
            if file_path.suffix.lower() not in BOOK_EXTENSIONS:
                continue
            abs_path = str(file_path.resolve())
            if abs_path not in known_files:
                orphan_paths.append(abs_path)
    return orphan_paths

def delete_orphan_books(orphan_paths: list, dry_run: bool = False, force: bool = False):
    """删除孤儿电子书文件，可预览或跳过确认"""
    if not orphan_paths:
        print("没有发现孤儿电子书文件。", file=sys.stderr)
        return

    print(f"发现 {len(orphan_paths)} 个孤儿电子书文件：", file=sys.stderr)
    for p in orphan_paths:
        print(f"  {p}", file=sys.stderr)

    if dry_run:
        print("DRY RUN 模式：以上文件不会被删除。", file=sys.stderr)
        return

    if not force:
        confirm = input("\n确认永久删除以上文件吗？(yes/no): ").strip().lower()
        if confirm != 'yes':
            print("取消删除操作。", file=sys.stderr)
            return

    deleted_count = 0
    for p in orphan_paths:
        try:
            Path(p).unlink()
            print(f"已删除: {p}")
            deleted_count += 1
        except Exception as e:
            print(f"删除失败 {p}: {e}", file=sys.stderr)

    print(f"成功删除 {deleted_count} 个文件。", file=sys.stderr)

def main():
    parser = argparse.ArgumentParser(description="Calibre 书库工具")
    parser.add_argument("--library", required=True, help="书库根目录 (例如 /home/user/Calibre书库)")
    parser.add_argument("--db", help="metadata.db 文件路径 (默认: 书库根目录/metadata.db)")
    parser.add_argument("--export-titles", action="store_true", help="导出所有书名")
    parser.add_argument("--titles-output", help="书名输出文件 (可选，不指定则打印到屏幕)")
    parser.add_argument("--find-orphans", action="store_true", help="查找孤儿电子书文件")
    parser.add_argument("--delete-orphans", action="store_true", help="删除孤儿电子书文件 (默认需确认)")
    parser.add_argument("--dry-run", action="store_true", help="预览模式：列出将被删除的文件但不实际删除")
    parser.add_argument("--force", action="store_true", help="跳过删除确认提示")
    args = parser.parse_args()

    library_root = Path(args.library).resolve()
    if not library_root.is_dir():
        print(f"错误: 书库目录不存在 '{library_root}'", file=sys.stderr)
        sys.exit(1)

    db_path = Path(args.db) if args.db else library_root / "metadata.db"
    if not db_path.is_file():
        print(f"错误: 数据库文件不存在 '{db_path}'", file=sys.stderr)
        sys.exit(1)

    # 功能1: 导出书名
    if args.export_titles:
        export_book_titles(db_path, args.titles_output)

    # 功能2 & 3: 查找并可选删除孤儿文件
    if args.find_orphans or args.delete_orphans:
        print("正在加载数据库中的已知文件...", file=sys.stderr)
        known = load_known_files(db_path, library_root)
        print(f"已加载 {len(known)} 个已知文件", file=sys.stderr)

        print("正在扫描书库...", file=sys.stderr)
        orphans = find_orphan_books(library_root, known)

        if args.find_orphans:
            if orphans:
                print("\n".join(orphans))
                print(f"共 {len(orphans)} 个孤儿电子书文件", file=sys.stderr)
            else:
                print("未发现孤儿电子书文件", file=sys.stderr)

        if args.delete_orphans:
            delete_orphan_books(orphans, dry_run=args.dry_run, force=args.force)

    if not (args.export_titles or args.find_orphans or args.delete_orphans):
        parser.print_help()

if __name__ == "__main__":
    main()