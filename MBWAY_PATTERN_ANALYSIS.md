# MB WAY - Análise de Padrão Definitiva

## Testes Sistemáticos Realizados

### ✅ Números que FUNCIONAM (Status 200)
```
912345678 ✓
918765432 ✓
919876543 ✓
966123456 ✓
963456789 ✓
```

### ❌ Números que FALHAM (Status 500)
```
912345679 ✗ (mudou 1 dígito do 912345678)
912345670 ✗ (mudou 1 dígito do 912345678)
911111111 ✗ (padrão sequencial)
919999999 ✗ (padrão repetido)
921876382 ✗ (prefixo 92)
925678901 ✗ (prefixo 92)
928765432 ✗ (prefixo 92)
934567890 ✗ (prefixo 93)
938765432 ✗ (prefixo 93)
967890123 ✗ (prefixo 96)
961234567 ✗ (prefixo 96)
915555555 ✗ (prefixo 91)
925555555 ✗ (prefixo 92)
935555555 ✗ (prefixo 93)
965555555 ✗ (prefixo 96)
```

## Conclusão

**NÃO há padrão matemático ou de prefixo.**

A conta WayMB possui uma **WHITELIST de números específicos** permitidos para MB WAY.

### Características da Whitelist:
- Não depende do prefixo (91, 92, 93, 96)
- Não depende do padrão numérico
- Não depende do nome ou NIF do pagador
- São números ESPECÍFICOS hardcoded no sistema

### Evidências de Modo Sandbox:
1. ✅ Multibanco funciona com QUALQUER número
2. ❌ MB WAY só funciona com números whitelisted
3. ✅ Mudança de 1 dígito causa falha total
4. ✅ Mesmo payload, resultados diferentes por método

## Solução

**Contactar WayMB Support:**

Perguntar:
- "A conta está em modo sandbox/teste?"
- "Como ativar modo produção para MB WAY?"
- "Qual a lista completa de números de teste?"

**Ou usar apenas Multibanco** (100% funcional em produção)

## Números de Teste Confirmados

Para testes internos, usar:
- `912345678`
- `918765432`
- `966123456`
