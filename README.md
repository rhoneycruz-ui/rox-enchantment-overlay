# ROX Enchantment Overlay

Aplicativo nativo e local para estimar, em tempo real, quanto falta gastar no encantamento de Prontera em Ragnarok X. Ele reconhece arma, armadura ou acessório, lê o nível e a barra de progresso e mostra um painel compacto ao lado do menu do jogo.

## Como usar

1. Extraia todo o ZIP para uma pasta comum. Não execute o programa de dentro do ZIP.
2. Abra `ROX Enchantment Overlay.exe`.
3. Na janela de configuração, selecione a janela do Ragnarok X.
4. Informe o preço **unitário** atual do Muspellium.
5. Ajuste a opacidade entre 25% e 100% e clique em **Monitorar janela**.
6. No jogo, abra o menu de encantamento de Prontera e selecione arma, armadura ou acessório.

O painel aparece após três leituras consistentes e desaparece quando o menu de encantamento é fechado. Ele fica à esquerda do painel do jogo sempre que houver espaço, permanece por cima e não intercepta cliques. Todas as opções continuam acessíveis pela janela de configuração e pelo ícone na bandeja do Windows.

## O que é reconhecido

- Arma / `Weapon`
- Armadura / `Armor` / `Armour`
- Acessório / `Accessory`
- Níveis 1 a 20
- Interface em português ou inglês
- Diferentes resoluções e escalas da janela do jogo

Os custos de Prontera usados são 90 Muspellium por clique de arma (3 pontos) e 30 por clique de armadura ou acessório (1 ponto). A tabela local de pontos para subir vai de 10 pontos no nível 1→2 até 12.550 pontos no nível 19→20.

## Estados e solução de problemas

**Aguardando painel:** a janela foi selecionada, mas o menu de encantamento ainda não foi reconhecido. Abra o menu completo, sem outra janela cobrindo o título e a barra. Aguarde cerca de um segundo.

**Janela indisponível:** restaure o jogo se estiver minimizado. Se o jogo foi fechado e reaberto, clique em **Redetectar**, selecione-o novamente e use **Monitorar janela**.

**O overlay não aparece:** prefira modo janela ou janela sem bordas. Tela cheia exclusiva é suportada apenas em caráter best-effort pelo Windows; alternar para janela sem bordas costuma resolver. Confirme também que o menu aberto é o de encantamento de Prontera.

**Valor incorreto:** o campo pede o preço de uma unidade de Muspellium, não o valor do pacote. A leitura da barra é visual e representa uma estimativa; pequenas diferenças de arredondamento podem ocorrer perto das divisões de cada clique.

**Antivírus/SmartScreen:** o executável é local e não assinado, então o Windows pode exibir um aviso na primeira execução. Distribua somente o ZIP original e confira o hash informado junto do pacote.

## Privacidade

O programa funciona inteiramente no computador. Não envia imagens, preços, nomes de janela ou telemetria pela internet e não salva capturas durante o uso normal. A configuração local contém apenas preço, opacidade e o título da janela selecionada.

Existe um utilitário de diagnóstico para desenvolvimento em `scripts/fixture_capture.py`. Ele exige um caminho de saída e a opção explícita `--confirm-save`; sem essa confirmação, nenhuma imagem é gravada. Revise a tela antes de compartilhar qualquer captura, pois ela pode conter informações privadas.

## Desenvolvimento

Requer Python 3.12 no Windows:

```powershell
python -m venv .venv
.venv\Scripts\python -m pip install -e ".[dev]"
$env:QT_QPA_PLATFORM="offscreen"
.venv\Scripts\python -m pytest -v
```

Para gerar a distribuição:

```powershell
.venv\Scripts\pyinstaller --clean --noconfirm packaging\rox-overlay.spec
```

## Componentes de terceiros

O pacote inclui Tesseract OCR sob Apache 2.0, modelos oficiais `tessdata_fast` para português e inglês e a fonte Inter sob SIL Open Font License. As licenças acompanham os respectivos arquivos.

| Arquivo | SHA-256 |
|---|---|
| `tesseract.exe` | `C0928EB1F453A4DF23432227F87BF7FE8530534EADABABCA471A31FF58CECA63` |
| `eng.traineddata` | `7D4322BD2A7749724879683FC3912CB542F19906C83BCC1A52132556427170B2` |
| `por.traineddata` | `C4932B937207A9514B7514D518B931A99938C02A28A5A5A553F8599ED58B7DEB` |

## Matriz de validação

| Ambiente | Resolução | Idioma | Resultado |
|---|---:|---|---|
| Windows 11, fixtures reais fornecidas | 1338×696 | Português | painel, armadura, nível e progresso reconhecidos |
| Windows 11, fixtures redimensionadas | múltiplas escalas | Português | painel localizado e regiões extraídas |
| Windows 11, fixtures OCR sintéticas | variável | Inglês | Weapon, Armor, Armour e Accessory reconhecidos |

O teste final dentro de uma sessão real do jogo deve ser repetido no computador de destino, principalmente para modo de tela, escala do Windows e versão da interface.
