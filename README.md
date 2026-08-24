# Построение ПСПФ булевых функций

Проект строит ПСПФ по номеру булевой функции с помощью алгоритма из `references/doi.org_10.4213_dm1658.pdf`
и добавляет построенные выражения в LaTeX-таблицы вида `references/tex_data.txt`.

## Установка uv

Установите uv по официальной инструкции:
https://docs.astral.sh/uv/getting-started/installation/

## Запуск

```bash
uv sync
uv run main.py calculate --k=4 27031
uv run main.py generate_table --k=4 --out=out.tex references/tex_data.txt
uv run main.py generate_table --k=4 --no-length --out=out.tex references/tex_data.txt
```

Число переменных, `k` по умолчанию равно 4.
При `k >= 5` программа предупреждает об экспоненциальном росте вычислений, но продолжает работу.

Команда `calculate` выводит построенное выражение в стандартный вывод.
Команда `generate_table` записывает обогащённую таблицу в файл, указанный параметром `--out`.
По умолчанию между оптимальной и построенной ПСПФ добавляется столбец `Длина построенной`
с количеством верхнеуровневых слагаемых построенной ПСПФ. Флаг `--no-length` отключает этот
столбец и сохраняет прежний четырёхколоночный формат результата.

### Тесты

```bash
uv run pytest
uv run ruff check .
uv run ruff format --check .
uv run pre-commit run --all-files
```
