# Changelog

## 1.2.1

### Correções
- O nível mostrado ficava preso no primeiro valor lido quando arma, armadura e acessório estavam em níveis diferentes (ex.: 15 e 16), ou depois de subir de nível. O nível agora é relido ao trocar de menu, depois de no máximo 2 leituras reaproveitadas e sempre que a barra de progresso volta ao começo.

## 1.2.0

### Novidades
- Escolha da cidade do encantamento (8 cidades). Fora de Prontera, o overlay mostra quantas pedras de encantamento e toques faltam.
- **Cidade automática:** o programa reconhece a pedra do quadro "Custo" e descobre a cidade sozinho. Se não reconhecer, usa a cidade escolhida (o overlay mostra "(manual)").
- O overlay some logo depois que o menu fecha: um botão redondo da interface do jogo era confundido com o painel (o detector agora exige pontuação 0,85; painéis reais dão 0,95 ou mais).
- Nova janela de configurações: horizontal, em três cartões (Jogo, Cálculo, Autoclique), com interruptores deslizantes e botões em degradê.
- Interruptor "Ativar autoclique" (desligado por padrão): desligado, o botão e o atalho não fazem nada e a tecla fica livre.
- Tabelas em `data/enchant_tables.json`, conferidas com rox.methax.com em todos os níveis e cidades.

## 1.1.0

### Correções
- O overlay não fica mais por cima de outros programas: ele se esconde quando o jogo perde o foco.
- Falhas de OCR ou captura não interrompem mais o monitoramento nem deixam valores antigos na tela; tudo é registrado em log.
- O botão Pausar/Retomar acompanha o estado real do monitoramento.
- Um campo inválido ou desconhecido na configuração não apaga mais todas as preferências.
- Os deslocamentos X/Y do painel, antes salvos e ignorados, agora funcionam.
- A configuração é salva 0,6 s depois da última alteração, em vez de a cada tecla.
- Valores inválidos de preço ou nível não geram mais exceções dentro do loop.
- Duas janelas com o mesmo título usam a captura por região da janela escolhida.
- O programa não abre duas vezes (instância única).

### Desempenho
- A busca do painel procura primeiro perto da última posição e escala: cerca de 2 ms por quadro, contra cerca de 230 ms antes, medido no print de teste `game-full.png`.
- O pool de threads do OCR é reaproveitado, sem criar threads a cada quadro.
- A janela do jogo é reencontrada pelo identificador, sem listar todas as janelas a cada quadro.
- O status só é enviado à interface quando muda.

### Novidades
- Toques restantes no overlay.
- Custo acumulado até um nível-meta.
- Indicador "≈" para valores estimados e aviso de leitura incerta.
- Monitoramento automático da janela lembrada ao abrir.
- Tema escuro nas configurações, ícone próprio e versão visível.
- Tabelas do jogo em um arquivo de dados.

### Autoclique
- `SendInput` no lugar de `mouse_event`, que está obsoleto.
- Só clica com o jogo em foco e o cursor dentro dele.
- Para sozinho ao subir de nível, ao fechar o menu ou ao trocar de janela.
- Tecla de atalho configurável (F1 a F12) e contador de cliques.

### Projeto
- Configuração própria (`settings-v1.1.json`), que importa a da 1.0 sem alterá-la.
- Log rotativo em `%LOCALAPPDATA%\ROX Enchantment Overlay\logs`.
- CI com ruff, mypy e testes em Python 3.12 e 3.13.
- Workflow de release que gera o ZIP e o SHA-256 em máquina limpa e roda o autoteste do executável.
