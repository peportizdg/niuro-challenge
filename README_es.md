# Reviewer de etiquetas de transacciones

Versión en español de [README.md](README.md).

Un reviewer basado en un LLM para un motor de keywords "legacy" que etiqueta las transacciones
bancarias de pequeñas empresas, y el efecto de sus correcciones sobre una oferta de financiamiento.
Es la respuesta al take-home de AI Engineer de Fundo. El diseño, los resultados y los trade-offs
están en [SOLUTION_es.md](SOLUTION_es.md).

Requiere Python 3.10 o superior. Para reproducir los resultados no hace falta nada más: ni
paquetes ni API key.

## Reproducir los resultados (sin API key)

```bash
git clone <este repo> && cd niuro-challenge
python3 run.py            # reescribe output/report.md y output/flags.json a partir de cache/
git diff --stat output/   # vacío: mismo resultado que el commiteado
python3 -m unittest       # 18 tests; uno de ellos vuelve a correr el pipeline y compara el reporte
```

`run.py` lee los datos sintéticos de `data/`, los etiqueta con el motor de keywords, toma las
respuestas del modelo de `cache/` (un JSON por llamada, cuya clave es un hash del pedido completo) y
escribe:

- `output/report.md`: calidad del reviewer contra el ground truth, features de crédito y ofertas
  antes y después de la revisión, y las tablas de sensibilidad a errores de etiqueta.
- `output/flags.json`: cada transacción marcada, con la etiqueta del motor, la etiqueta propuesta,
  la confianza y el motivo. Es la cola de trabajo del underwriter.

## Volver a llamar al modelo

Solo hace falta para transacciones o prompts que no estén en el cache. Sirven las dos formas, y las
dos mandan el mismo pedido (modelo, prompt, schema, effort), así que comparten el cache.

Con una API key de Anthropic:

```bash
python3 -m venv .venv && . .venv/bin/activate
pip install -r requirements.txt
export ANTHROPIC_API_KEY=sk-ant-...
python3 run.py
```

Sin key, con un [Claude Code](https://claude.com/claude-code) logueado (`claude` en el PATH). Corre
en modo headless, sin herramientas ni configuración del usuario, y usa el plan de esa cuenta:

```bash
python3 run.py
```

Las llamadas que ya están en el cache no se repiten; para rehacerlas, primero hay que mover `cache/`
a otro lado. Si el modelo no está disponible, los negocios afectados se quedan con las etiquetas del
motor y el reporte indica cuántos no se revisaron.

## Correrlo sobre otras transacciones

```bash
python3 run.py ruta/a/transactions.json /tmp/out
```

El archivo puede ser una respuesta de `/transactions/get` de Plaid (`accounts` + `transactions`) o
una lista de transacciones de Plaid. Las transacciones se agrupan en negocios por `account_id`. Si
no hay un `truth.json` al lado del archivo, se omite la sección de calidad y se escribe el resto del
reporte. Las transacciones nuevas no están en el cache, así que hace falta una API key o un Claude
Code logueado.

## Regenerar los datos sintéticos

```bash
python3 generate.py       # determinístico (seed 42): escribe data/transactions.json y data/truth.json
```

## Archivos

| Archivo | Qué hace |
|---|---|
| `generate.py` | 10 negocios sintéticos, 90 días, formato Plaid. El ground truth va en un archivo aparte que el modelo nunca ve. |
| `labels.py` | Los 13 grupos y la regla de revenue. |
| `engine.py` | El motor de keywords, imperfecto a propósito. |
| `reviewer.py` | Prompt, llamada al modelo, validación de la respuesta, cache y aplicación de los flags confiables. |
| `credit.py` | Features de crédito, la regla de oferta y la sensibilidad a errores de etiqueta. |
| `run.py` | Corre todo y escribe el reporte. |
| `tests/` | `python3 -m unittest`, solo librería estándar. |
