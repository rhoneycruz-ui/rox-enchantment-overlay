# ROX Enchantment Overlay

[![Windows](https://img.shields.io/badge/Windows-10%20%7C%2011-42C8F5)](https://github.com/rhoneycruz-ui/rox-enchantment-overlay/releases/latest)
[![Release](https://img.shields.io/github/v/release/rhoneycruz-ui/rox-enchantment-overlay)](https://github.com/rhoneycruz-ui/rox-enchantment-overlay/releases/latest)
[![License: MIT](https://img.shields.io/badge/License-MIT-8FE13A.svg)](LICENSE)

Assistente gratuito e local para calcular, em tempo real, quanto falta gastar no encantamento de **Prontera** em Ragnarok X. O programa reconhece arma, armadura ou acessório, lê o nível e a barra de progresso e mostra uma sobreposição compacta ao lado do menu do jogo.

> O programa não modifica o jogo e não envia imagens ou dados pela internet. A leitura é feita visualmente na tela do próprio computador.

## Download

Baixe a versão mais recente na página de [Releases](https://github.com/rhoneycruz-ui/rox-enchantment-overlay/releases/latest).

O arquivo pronto para usar é `ROX-Enchantment-Overlay-portable.zip`. Depois do download, confira o SHA-256 publicado junto da mesma versão se quiser validar a integridade do arquivo.

## Recursos

- Reconhecimento automático de arma, armadura e acessório.
- Leitura de níveis 1 a 20 e do progresso para o próximo nível.
- Interface do jogo em português ou inglês.
- Compatibilidade com diferentes resoluções e escalas de janela.
- Cálculo dos pontos, Muspellium e cristais restantes.
- Ícone de cristal exibido ao lado do custo.
- Overlay compacto, transparente, sempre visível e que não bloqueia cliques.
- Opacidade configurável entre 25% e 100%.
- Autoclique opcional com contagem de 3 segundos.
- Atalho global **F1** para iniciar ou interromper o autoclique imediatamente.
- Funcionamento totalmente local e sem telemetria.

## Tutorial de instalação

1. Abra a página de [Releases](https://github.com/rhoneycruz-ui/rox-enchantment-overlay/releases/latest).
2. Baixe `ROX-Enchantment-Overlay-portable.zip`.
3. Extraia **todo o conteúdo** do ZIP para uma pasta comum. Não execute o programa diretamente de dentro do arquivo compactado.
4. Abra a pasta `ROX Enchantment Overlay` e execute `ROX Enchantment Overlay.exe`.
5. Como o executável é local e não possui assinatura digital, o Windows SmartScreen pode mostrar um aviso na primeira execução. Confirme apenas se o arquivo veio desta página oficial e o hash está correto.

Não é necessário instalar Python, Tesseract ou qualquer dependência adicional.

## Tutorial de uso

1. Abra o Ragnarok X em modo janela ou janela sem bordas.
2. Execute o ROX Enchantment Overlay.
3. Na janela de configuração, selecione a janela do Ragnarok X.
4. Informe o preço **unitário** atual de um Muspellium em cristais.
5. Escolha a opacidade desejada e clique em **Monitorar janela**.
6. No jogo, abra o menu de encantamento de Prontera.
7. Selecione uma arma, armadura ou acessório.

Depois de algumas leituras consistentes, o painel aparece automaticamente à esquerda do menu de encantamento. Ele mostra o nível atual, o próximo nível, os pontos restantes, o Muspellium necessário e o custo restante em cristais.

O painel desaparece quando o menu de encantamento é fechado. Ele permanece sobre o jogo e não intercepta os cliques do mouse.

## Autoclique opcional

1. Pressione **F1** em qualquer janela ou clique em **Iniciar autoclique** nas configurações.
2. Durante a contagem de 3 segundos, posicione o cursor sobre o botão **Refino** do jogo.
3. O programa fará 4 cliques por segundo na posição atual do cursor.
4. Pressione **F1** novamente para interromper imediatamente, inclusive durante a contagem.

O botão **Parar autoclique** e o fechamento do programa também interrompem os cliques. Se outro aplicativo já estiver usando F1, a configuração mostrará **F1 indisponível — use o botão**.

> Confira as regras do jogo antes de usar qualquer automação. O uso do autoclique é opcional e de responsabilidade do usuário.

## Valores usados no cálculo

Em Prontera:

- Arma: 90 Muspellium por clique, concedendo 3 pontos.
- Armadura: 30 Muspellium por clique, concedendo 1 ponto.
- Acessório: 30 Muspellium por clique, concedendo 1 ponto.

Nos três casos, o custo efetivo é de 30 Muspellium por ponto. A tabela local cobre todos os níveis, de 10 pontos para `1 → 2` até 12.550 pontos para `19 → 20`.

## Solução de problemas

### Aguardando painel

A janela foi selecionada, mas o menu de encantamento ainda não foi reconhecido. Abra o menu completo, deixe o título e a barra visíveis e aguarde cerca de um segundo.

### Janela indisponível

Restaure o jogo se estiver minimizado. Se o jogo foi fechado e aberto novamente, clique em **Redetectar**, selecione a janela e use **Monitorar janela**.

### O overlay não aparece

Prefira modo janela ou janela sem bordas. Tela cheia exclusiva depende do comportamento do Windows e pode impedir a sobreposição. Confirme também que o menu aberto é o encantamento de Prontera.

### O tipo do item ou o valor parece incorreto

Deixe o nome abaixo do item e a barra de progresso totalmente visíveis. O campo de preço pede o valor de **uma unidade** de Muspellium, não o preço de um pacote. A leitura da barra é visual, então pequenas diferenças de arredondamento podem ocorrer perto das divisões de cada clique.

### Aviso de antivírus ou SmartScreen

O aplicativo é empacotado localmente e ainda não possui assinatura digital. Baixe somente pela página oficial de Releases e compare o SHA-256 com o arquivo publicado junto da versão.

## Privacidade

O programa funciona inteiramente no computador. Ele não envia capturas, preços, nomes de janela ou telemetria pela internet. A configuração local guarda apenas o preço informado, a opacidade e o título da janela selecionada.

## Desenvolvimento

Requer Python 3.12 no Windows:

```powershell
python -m venv .venv
.venv\Scripts\python -m pip install -e ".[dev]"
$env:QT_QPA_PLATFORM="offscreen"
.venv\Scripts\python -m pytest -v
```

Para gerar a distribuição portátil:

```powershell
.\scripts\build_release.ps1
```

O projeto inclui testes da lógica de cálculo, reconhecimento, interface, autoclique, atalho global e composição do aplicativo.

## Componentes de terceiros

O pacote inclui bibliotecas e recursos de terceiros, entre eles PySide6/Qt, OpenCV, NumPy, Tesseract OCR, modelos oficiais `tessdata_fast` e a fonte Inter. O inventário, os links dos projetos e as licenças aplicáveis estão em [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md). Os textos completos das licenças acompanham a distribuição portátil.

| Arquivo | SHA-256 |
|---|---|
| `tesseract.exe` | `C0928EB1F453A4DF23432227F87BF7FE8530534EADABABCA471A31FF58CECA63` |
| `eng.traineddata` | `7D4322BD2A7749724879683FC3912CB542F19906C83BCC1A52132556427170B2` |
| `por.traineddata` | `C4932B937207A9514B7514D518B931A99938C02A28A5A5A553F8599ED58B7DEB` |

## Aviso

Este é um projeto independente, sem vínculo oficial com Ragnarok X, Nuverse, Gravity ou suas afiliadas. As marcas e imagens do jogo pertencem aos respectivos proprietários.

## Licença

O código original deste projeto é distribuído sob a [licença MIT](LICENSE). Bibliotecas, fontes, modelos OCR e materiais visuais relacionados ao jogo permanecem sob suas próprias licenças ou direitos e não são relicenciados pela MIT; consulte [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md).

Licenciado por Rhoney.
