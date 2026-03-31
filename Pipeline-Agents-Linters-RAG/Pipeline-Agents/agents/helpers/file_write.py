import os


def write_files_safely(data_dict: dict, base_path: str = "", mode: str = "create") -> None:
    """
    Zapisuje pliki z data_dict do base_path.
    W trybie 'modify' pomija pliki, których zawartość nie zmieniła się.
    """
    for key, value in data_dict.items():
        full_path = os.path.join(base_path, key)
        if isinstance(value, dict):
            os.makedirs(full_path, exist_ok=True)
            write_files_safely(value, full_path, mode)
            continue

        dir_name = os.path.dirname(full_path)
        if dir_name:
            os.makedirs(dir_name, exist_ok=True)

        new_content = str(value)

        if mode == "modify" and os.path.exists(full_path):
            with open(full_path, "r", encoding="utf-8") as f:
                existing_content = f.read()
            if existing_content == new_content:
                print(f"  [skip] {key} — bez zmian")
                continue
            print(f"  [update] {key}")
        else:
            print(f"  [write] {key}")

        with open(full_path, "w", encoding="utf-8") as f:
            f.write(new_content)
