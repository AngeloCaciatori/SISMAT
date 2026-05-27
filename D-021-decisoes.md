# D-021 — 2026-05-12 — Resumo das decisões

## Visual
- Brasão real PNG ativo em todos os templates
- Topbar de impressão navy em todos os 4 templates de impressão
- conferencia.html: grupo-tipo navy + cabeçalho institucional com brasão
- base.html: bloco content único (fix do Internal Server Error)
- Sidebar: "Dashboard" → "Pagina Inicial"
- Botão Logout: fundo vermelho escuro #7f1d1d, tamanho normal, ícone 🚪

## Permissões
- efetivo.py + material.py: @admin_required removido de CRUD (mantém @login_required)
- cautelas: cancelar + reabrir mantidos admin-only
- operadores.py: 9 @admin_required intactos
- Templates: guards is_admin removidos de efetivo/lista, efetivo/detalhe, material/lista

## Documentação
- documentacao.py: CRUD completo (lista, novo, editar, duplicar, excluir, gerar)
- Templates: lista.html, editor.html (WYSIWYG contenteditable), gerar.html (standalone print)
- Variáveis {{NOME_INSTITUICAO}}, {{DATA_HOJE}}, {{OPERADOR}}, etc. com substituição em gerar()
- Modelos padrão (FIDU + Devolução) não excluíveis, apenas editáveis/duplicáveis
