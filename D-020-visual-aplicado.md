# D-020 — Reestruturação visual SISMAT (2026-05-12)

## Arquivos alterados (somente HTML/CSS)

| Arquivo | Alteração |
|---------|-----------|
| `app/static/css/sismat.css` | Reescrito completo (474 linhas). Paleta navy+dourado. |
| `app/static/img/brasao_sismat.svg` | **Criado** — brasão placeholder (substituir pelo PNG real) |
| `app/templates/base.html` | Reescrito — sidebar 200px + topbar sticky + JS de nav ativo |
| `app/templates/dashboard.html` | Redesenhado — stat pills gradiente + nav-cards coloridos |
| `app/templates/login.html` | Reestilizado — gradiente navy, brasão SVG, card branco |
| `app/templates/recuperar.html` | Reestilizado — mesmo padrão do login |
| `app/templates/material/lista.html` | Corrigido rgba verde hardcoded → navy |
| `app/templates/operadores/backup.html` | Corrigido rgba verde hardcoded → dourado |

## Templates de impressão — NÃO TOCADOS
- `cautelas/imprimir_ficha.html`
- `efetivo/imprimir_cautelas.html`
- `material/conferencia.html`
- `material/imprimir_prateleira.html`

## Zero arquivos .py alterados ✓

## Para integrar o brasão PNG real
1. Copie `BrasaoSISMAT.png` para: `C:\sismat\app\static\img\brasao_sismat.png`
2. Em `base.html` linha ~19: troque `brasao_sismat.svg` por `brasao_sismat.png`
3. Em `login.html` linha ~9: troque `brasao_sismat.svg` por `brasao_sismat.png`
4. Em `recuperar.html` linha ~9: troque `brasao_sismat.svg` por `brasao_sismat.png`
5. Em `dashboard.html` linha ~4: troque `brasao_sismat.svg` por `brasao_sismat.png`

## Referência visual
Template Logistix Admin (screenshots enviados pelo Angelo em 2026-05-12).
