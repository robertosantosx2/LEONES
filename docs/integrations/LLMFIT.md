# LLMFit / FitLLM — RC4 recomendador opcional

**Estado RC3:** fuera del camino canónico (histórico).  
**Estado RC4:** recomendador **opcional** de modelo (ESTIMATED).

## Frontera RC4

- LEONES **arranca sin** FitLLM.
- FitLLM **no** autoriza ejecución ni produce MEASURED.
- El usuario puede elegir modelo **sin** FitLLM.
- Tras instalar Magnitude u ODS, se puede **ofrecer** desinstalar FitLLM (opt-in).

## Entrada de código

```bash
python3 scripts/rc4_fitllm_recommend.py --json
```

Envelope: `leones.rc4.fitllm_recommendation.v1` con
`execution_authorized: false`, `kind: ESTIMATED`.

## Autoridad

> LEONES descubre el hardware. FitLLM puede recomendar. El usuario elige.
> Magnitude u ODS ejecutan. LEONES verifica, mide y sentencia.

## Costes e uninstall

Ver `docs/LEONES-INTERFACE-RULES.md` y `scripts/rc4_component_cost.py`.
