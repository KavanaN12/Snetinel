import pathlib, sys
import yaml
for path in ['render.yaml', 'backend/render.yaml']:
    with pathlib.Path(path).open('r', encoding='utf-8') as fh:
        yaml.safe_load(fh)
    print(f'YAML_OK {path}')
print('VALIDATION_OK')
