# ROX Enchantment Overlay Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Criar um aplicativo portátil para Windows que reconheça o painel de encantamento de Ragnarok X e exiba, em uma sobreposição compacta, o custo restante em Muspellium e Zeny.

**Architecture:** Um pipeline em worker captura apenas a janela do jogo, localiza e normaliza o painel, reconhece tipo/nível/progresso e estabiliza os resultados antes de publicá-los. Um núcleo de domínio puro calcula custos; a thread de UI PySide6 renderiza a sobreposição click-through e a janela de configurações sem depender dos detalhes de captura ou OCR.

**Tech Stack:** Python 3.12, PySide6, OpenCV, NumPy, Tesseract OCR com dados `por` e `eng`, captura Windows Graphics Capture com fallback MSS, pytest, PyInstaller.

**Spec:** `docs/superpowers/specs/2026-10-16-rox-enchantment-overlay-design.md`

## Global Constraints

- Suportar Windows 10 e 11; modo janela ou janela sem bordas é a base suportada, e tela cheia exclusiva é best-effort.
- Processar tudo localmente; não transmitir capturas, títulos de janela, OCR ou telemetria.
- Não clicar, injetar código, ler memória nem modificar o processo do jogo.
- Suportar Prontera, níveis 1–20 e títulos em português e inglês.
- Capturar somente a janela selecionada com alvo de 5 quadros por segundo.
- Manter captura/reconhecimento fora da thread da UI.
- Exibir somente leituras estabilizadas; ocultar valores incertos.
- Sobreposição compacta, click-through, ancorada 12 px à esquerda do painel, com fundo de 25–100% de opacidade e padrão de 82%.
- Distribuir como ZIP portátil com executável e dependências, sem exigir Python instalado.

## Review Focus

- OCR parcialmente errado (`NiveI`, acento ausente, `armour`) deve ainda classificar palavras distintivas ou retornar desconhecido, nunca o tipo errado; coberto na Task 2.
- Barra vazia, quase cheia ou afetada por brilho deve produzir faixa válida e estabilizada, ou ser rejeitada; coberto na Task 3.
- Arma com pontos restantes não divisíveis por três deve arredondar cliques para cima sem subestimar Muspellium; coberto na Task 1.
- Janela movida, redimensionada ou perto da borda de outro monitor deve manter overlay dentro da área útil; coberto na Task 7.
- Painel que fecha, reaparece ou alterna leituras incompatíveis deve ocultar/reexibir sem dados obsoletos; coberto nas Tasks 3 e 6.

---

## File Structure

```text
pyproject.toml                         dependências, pytest e metadados
.gitignore                             ambientes, builds, logs e configurações locais
src/rox_overlay/app.py                 composição do aplicativo e ponto de entrada
src/rox_overlay/domain.py              tabela, tipos e cálculo puro
src/rox_overlay/config.py              configurações validadas e persistência JSON
src/rox_overlay/recognition/models.py  contratos de detecção e leitura
src/rox_overlay/recognition/text.py    normalização e OCR de tipo/nível
src/rox_overlay/recognition/panel.py   localização e normalização do painel
src/rox_overlay/recognition/progress.py leitura visual da barra
src/rox_overlay/recognition/stability.py estabilização temporal
src/rox_overlay/recognition/pipeline.py composição do reconhecimento de um frame
src/rox_overlay/capture/base.py        protocolos de janela e captura
src/rox_overlay/capture/windows.py     descoberta e captura primária Windows
src/rox_overlay/capture/fallback.py    captura MSS por região visível
src/rox_overlay/ui/overlay.py          janela click-through e layout compacto
src/rox_overlay/ui/settings.py         formulário de configuração
src/rox_overlay/ui/tray.py             menu e estado da bandeja
src/rox_overlay/controller.py          worker, estado e coordenação UI/pipeline
packaging/rox-overlay.spec             configuração PyInstaller
tests/                                 testes unitários e de integração
tests/fixtures/                        capturas/crops aprovados e manifests
scripts/fixture_capture.py             captura explícita para diagnóstico/testes
README.md                              instalação, uso e solução de problemas
```

### Task 1: Scaffold e núcleo de cálculo

**Files:**
- Create: `pyproject.toml`
- Create: `.gitignore`
- Create: `src/rox_overlay/__init__.py`
- Create: `src/rox_overlay/domain.py`
- Create: `tests/test_domain.py`

**Interfaces:**
- Consumes: nenhum código anterior.
- Produces: `ItemType`, `EnchantRequirement`, `CostEstimate`, `requirement_for(level)`, `estimate_cost(item_type, level, progress, unit_price)`.

- [ ] **Step 1: Inicializar o repositório e o ambiente de testes**

Criar `pyproject.toml` para Python `>=3.12,<3.13`, layout `src`, pytest e dependências de desenvolvimento; criar `.gitignore`; executar `git init` se a pasta ainda não for um repositório.

- [ ] **Step 2: Escrever os testes falhos da tabela e das fórmulas**

Em `tests/test_domain.py`, afirmar os 19 valores da tabela, `requirement_for(20) is None`, armadura 14→15 a 37% com preço 84, e arma com pontos restantes não divisíveis por 3:

```python
def test_armor_level_14_at_37_percent():
    result = estimate_cost(ItemType.ARMOR, level=14, progress=0.37, unit_price=84)
    assert result.remaining_points == 2_394
    assert result.remaining_muspellium == 71_820
    assert result.remaining_zeny == 6_032_880

def test_weapon_rounds_remaining_taps_up():
    result = estimate_cost(ItemType.WEAPON, level=2, progress=0.01, unit_price=84)
    assert result.remaining_taps == 10
    assert result.remaining_muspellium == 900
```

- [ ] **Step 3: Executar o teste e confirmar falha**

Run: `python -m pytest tests/test_domain.py -v`
Expected: FAIL por módulo ou símbolos ainda inexistentes.

- [ ] **Step 4: Implementar o domínio puro**

Em `domain.py`, criar:

```python
class ItemType(StrEnum): WEAPON = "weapon"; ARMOR = "armor"; ACCESSORY = "accessory"
@dataclass(frozen=True) class EnchantRequirement: current_level: int; next_level: int; points: int
@dataclass(frozen=True) class CostEstimate: item_type: ItemType; current_level: int; next_level: int | None; progress: float; remaining_points: int; remaining_taps: int; remaining_muspellium: int; remaining_zeny: int; is_max_level: bool
def requirement_for(level: int) -> EnchantRequirement | None: ...
def estimate_cost(item_type: ItemType, level: int, progress: float, unit_price: int) -> CostEstimate: ...
```

Validar nível 1–20, progresso 0–1 e preço inteiro não negativo. Implementar exatamente a tabela e as fórmulas da especificação.

- [ ] **Step 5: Executar os testes do domínio**

Run: `python -m pytest tests/test_domain.py -v`
Expected: PASS para tabela, validação, máximo nível e arredondamentos.

- [ ] **Step 6: Commit**

```bash
git add pyproject.toml .gitignore src/rox_overlay tests/test_domain.py
git commit -m "feat: add enchantment cost domain"
```

### Task 2: Reconhecimento bilíngue de tipo e nível

**Files:**
- Create: `src/rox_overlay/recognition/__init__.py`
- Create: `src/rox_overlay/recognition/models.py`
- Create: `src/rox_overlay/recognition/text.py`
- Create: `tests/recognition/test_text.py`

**Interfaces:**
- Consumes: `ItemType` da Task 1; imagem `numpy.ndarray` em BGR.
- Produces: `Rect`, `FieldReading[T]`, `normalize_ocr_text(text)`, `classify_item_type(text)`, protocolo `OcrEngine`, `read_item_type(image, ocr)`, `read_level(image, ocr)`.

- [ ] **Step 1: Escrever testes falhos para normalização e classificação**

Cobrir `Nível da Arma`, `Nivel da Armadura`, `NÍVEL DO ACESSÓRIO`, `Weapon Level`, `Armor Level`, `Armour Level`, `Accessory Level`, OCR ruidoso `NiveI da Arma` e texto sem palavra distintiva. O último deve retornar `None`, nunca adivinhar.

- [ ] **Step 2: Escrever testes falhos para leitura do nível**

Usar um `FakeOcrEngine` que devolva `14`, ` 19 `, `I4`, `21` e vazio. Aceitar 1–20; normalizar confusão inequívoca `I4`→`14`; rejeitar 21 e vazio com confiança zero.

- [ ] **Step 3: Executar os testes e confirmar falha**

Run: `python -m pytest tests/recognition/test_text.py -v`
Expected: FAIL por módulos ainda inexistentes.

- [ ] **Step 4: Implementar contratos e normalização**

Em `models.py`:

```python
@dataclass(frozen=True) class Rect: x: int; y: int; width: int; height: int
@dataclass(frozen=True) class FieldReading(Generic[T]): value: T | None; confidence: float; raw: str = ""
@runtime_checkable class OcrEngine(Protocol):
    def read_line(self, image: np.ndarray, *, languages: tuple[str, ...], digits_only: bool = False) -> FieldReading[str]: ...
```

Em `text.py`, remover acentos, normalizar caixa/espaços e usar correspondência conservadora dos tokens `arma/weapon`, `armadura/armor/armour`, `acessorio/accessory`. Aplicar pré-processamento de contraste e escala antes de chamar o OCR.

- [ ] **Step 5: Executar os testes de texto**

Run: `python -m pytest tests/recognition/test_text.py -v`
Expected: PASS para português, inglês, ruído e rejeições.

- [ ] **Step 6: Commit**

```bash
git add src/rox_overlay/recognition tests/recognition/test_text.py
git commit -m "feat: recognize enchantment type and level"
```

### Task 3: Leitura da barra e estabilização temporal

**Files:**
- Create: `src/rox_overlay/recognition/progress.py`
- Create: `src/rox_overlay/recognition/stability.py`
- Create: `tests/recognition/test_progress.py`
- Create: `tests/recognition/test_stability.py`
- Create: `tests/fixtures/progress/manifest.json`
- Create: `tests/fixtures/progress/*.png`

**Interfaces:**
- Consumes: crop BGR da barra e `FieldReading` da Task 2.
- Produces: `read_progress(image) -> FieldReading[float]`, `RecognizedState`, `StableState`, `ReadingStabilizer.push(reading)`, `ReadingStabilizer.mark_invalid()`.

- [ ] **Step 1: Adicionar fixtures mínimas da barra**

Recortar das imagens fornecidas exemplos vazio/parcial e criar crops controlados quase cheio; registrar em `manifest.json` a faixa de progresso esperada de cada crop.

- [ ] **Step 2: Escrever testes falhos da segmentação**

Para cada fixture, afirmar que `read_progress` fica dentro da faixa do manifest. Adicionar imagens com track ausente e brilho sem preenchimento; ambas devem retornar `value is None`.

- [ ] **Step 3: Implementar `read_progress`**

Detectar os limites do track, converter para HSV/Lab, combinar saturação/luminância do ciano, aplicar operações morfológicas leves e medir o maior preenchimento contíguo desde a borda inicial. Não usar um RGB único.

- [ ] **Step 4: Executar os testes da barra**

Run: `python -m pytest tests/recognition/test_progress.py -v`
Expected: PASS para vazio, parcial, quase cheio e rejeições.

- [ ] **Step 5: Escrever testes falhos do estabilizador**

Cobrir: publicação após três leituras compatíveis; mediana de sete progressos; nenhuma troca por um frame divergente; retenção por quatro falhas; ocultação na quinta; reaparecimento após três leituras novas.

- [ ] **Step 6: Implementar o estabilizador**

```python
@dataclass(frozen=True) class RecognizedState: item_type: ItemType; level: int; progress: float; confidence: float; panel_rect: Rect
@dataclass(frozen=True) class StableState: reading: RecognizedState | None; visible: bool
class ReadingStabilizer:
    def push(self, reading: RecognizedState) -> StableState: ...
    def mark_invalid(self) -> StableState: ...
```

Usar janela de sete valores, três leituras compatíveis para publicar e cinco inválidas para ocultar.

- [ ] **Step 7: Executar os testes de reconhecimento temporal**

Run: `python -m pytest tests/recognition/test_progress.py tests/recognition/test_stability.py -v`
Expected: PASS.

- [ ] **Step 8: Commit**

```bash
git add src/rox_overlay/recognition tests/recognition tests/fixtures/progress
git commit -m "feat: read and stabilize enchantment progress"
```

### Task 4: Detecção e normalização do painel

**Files:**
- Create: `src/rox_overlay/recognition/panel.py`
- Create: `tests/recognition/test_panel.py`
- Create: `tests/fixtures/panels/manifest.json`
- Create: `tests/fixtures/panels/*.png`

**Interfaces:**
- Consumes: frame BGR da janela.
- Produces: `PanelDetection`, `PanelRegions`, `PanelDetector.detect(frame)`, `PanelDetector.extract_regions(frame, detection)`.

- [ ] **Step 1: Preparar fixtures em várias escalas e posições**

Usar os prints fornecidos para criar casos de painel completo, painel ausente, painel deslocado e cópias redimensionadas. O manifest guarda retângulo esperado com tolerância relativa de 3%.

- [ ] **Step 2: Escrever testes falhos da localização**

Exigir IoU mínima de 0,85 nos casos positivos, `None` no negativo e regiões normalizadas não vazias para título, nível e barra.

- [ ] **Step 3: Implementar modelos e `PanelDetector`**

```python
@dataclass(frozen=True) class PanelDetection: rect: Rect; scale: float; confidence: float
@dataclass(frozen=True) class PanelRegions: title: np.ndarray; level: np.ndarray; progress: np.ndarray
class PanelDetector:
    def detect(self, frame: np.ndarray) -> PanelDetection | None: ...
    def extract_regions(self, frame: np.ndarray, detection: PanelDetection) -> PanelRegions: ...
```

Combinar proporção da moldura, círculo central e geometria da barra em pirâmide de escalas limitada; expressar crops como frações do retângulo detectado.

- [ ] **Step 4: Executar os testes do painel**

Run: `python -m pytest tests/recognition/test_panel.py -v`
Expected: PASS em escalas, deslocamentos e ausência.

- [ ] **Step 5: Commit**

```bash
git add src/rox_overlay/recognition/panel.py tests/recognition/test_panel.py tests/fixtures/panels
git commit -m "feat: detect enchantment panel across resolutions"
```

### Task 5: OCR real e pipeline de reconhecimento

**Files:**
- Create: `src/rox_overlay/recognition/tesseract.py`
- Create: `src/rox_overlay/recognition/pipeline.py`
- Create: `tests/recognition/test_tesseract.py`
- Create: `tests/recognition/test_pipeline.py`
- Create: `tests/fixtures/text/manifest.json`
- Create: `tests/fixtures/text/*.png`

**Interfaces:**
- Consumes: `PanelDetector`, `OcrEngine`, `read_item_type`, `read_level`, `read_progress`.
- Produces: `TesseractOcrEngine(tesseract_path, tessdata_dir)`, `RecognitionPipeline.recognize(frame) -> RecognizedState | None`.

- [ ] **Step 1: Fixar recursos OCR portáteis**

Adicionar ao ambiente de desenvolvimento o runtime Tesseract e os arquivos oficiais `eng.traineddata` e `por.traineddata`; registrar licenças e checksums no README de dependências.

- [ ] **Step 2: Criar fixtures de texto português/inglês**

Incluir crops reais em português dos prints fornecidos e crops ingleses de referência contendo `Weapon`, `Armor`, `Armour` e `Accessory`; o manifest define tipo/nível esperados.

- [ ] **Step 3: Escrever testes falhos do adaptador OCR**

Exigir que cada fixture produza o tipo/nível do manifest e que caminho de executável ausente gere erro de configuração legível, não crash genérico.

- [ ] **Step 4: Implementar `TesseractOcrEngine`**

Executar OCR em modo de linha única, `por+eng` para título e whitelist `0123456789` para nível; converter confiança da engine para 0–1.

- [ ] **Step 5: Escrever testes falhos do pipeline**

Com fakes determinísticos, cobrir painel ausente, campo obrigatório desconhecido, composição bem-sucedida e confiança final igual ao mínimo dos campos obrigatórios.

- [ ] **Step 6: Implementar `RecognitionPipeline`**

```python
class RecognitionPipeline:
    def __init__(self, panel_detector: PanelDetector, ocr: OcrEngine) -> None: ...
    def recognize(self, frame: np.ndarray) -> RecognizedState | None: ...
```

Rejeitar a leitura quando painel, tipo, nível ou progresso for inválido; preservar o retângulo do painel para posicionamento.

- [ ] **Step 7: Executar os testes de OCR e pipeline**

Run: `python -m pytest tests/recognition/test_tesseract.py tests/recognition/test_pipeline.py -v`
Expected: PASS em português, inglês, erros de configuração e composição.

- [ ] **Step 8: Commit**

```bash
git add src/rox_overlay/recognition tests/recognition tests/fixtures/text README.md
git commit -m "feat: integrate bilingual OCR pipeline"
```

### Task 6: Descoberta, captura e loop do controller

**Files:**
- Create: `src/rox_overlay/capture/__init__.py`
- Create: `src/rox_overlay/capture/base.py`
- Create: `src/rox_overlay/capture/windows.py`
- Create: `src/rox_overlay/capture/fallback.py`
- Create: `src/rox_overlay/controller.py`
- Create: `tests/capture/test_window_discovery.py`
- Create: `tests/test_controller.py`

**Interfaces:**
- Consumes: `RecognitionPipeline`, `ReadingStabilizer`, `estimate_cost`.
- Produces: `WindowInfo`, `FrameSource`, `WindowDiscovery`, `WindowsCaptureSource`, `MssCaptureSource`, `OverlaySnapshot`, `RecognitionController` Qt signals.

- [ ] **Step 1: Escrever testes falhos dos contratos de janela**

Cobrir enumeração somente de janelas visíveis, seleção persistida por identificador/título normalizado, múltiplos candidatos e reacquisição após mudança de handle.

- [ ] **Step 2: Definir protocolos de captura**

```python
@dataclass(frozen=True) class WindowInfo: handle: int; title: str; client_rect: Rect
class WindowDiscovery(Protocol):
    def list_windows(self) -> list[WindowInfo]: ...
    def reacquire(self, previous: WindowInfo) -> WindowInfo | None: ...
class FrameSource(Protocol):
    def capture(self, window: WindowInfo) -> np.ndarray | None: ...
```

- [ ] **Step 3: Implementar descoberta e os dois adaptadores de captura**

Usar Windows Graphics Capture como fonte primária e MSS como fallback da região visível. Retornar `None` em janela minimizada/indisponível e nunca bloquear indefinidamente.

- [ ] **Step 4: Escrever testes falhos do controller**

Com relógio, captura e pipeline falsos, cobrir alvo de 5 FPS, painel fecha por cinco frames, painel reaparece após três leituras, preço alterado durante execução e janela indisponível sem busy-loop.

- [ ] **Step 5: Implementar `RecognitionController`**

```python
@dataclass(frozen=True) class OverlaySnapshot: estimate: CostEstimate; panel_rect: Rect; confidence: float
class RecognitionController(QObject):
    snapshot_ready = Signal(object)
    overlay_hidden = Signal()
    status_changed = Signal(str)
    def start(self, window: WindowInfo) -> None: ...
    def pause(self) -> None: ...
    def resume(self) -> None: ...
    def stop(self) -> None: ...
    def set_unit_price(self, price: int) -> None: ...
```

Executar captura/reconhecimento em `QThread`; emitir apenas snapshots estabilizados para a UI.

- [ ] **Step 6: Executar testes de captura/controller**

Run: `python -m pytest tests/capture/test_window_discovery.py tests/test_controller.py -v`
Expected: PASS para seleção, reacquisição, frequência e fechamento/reabertura.

- [ ] **Step 7: Commit**

```bash
git add src/rox_overlay/capture src/rox_overlay/controller.py tests/capture tests/test_controller.py
git commit -m "feat: capture game window and publish stable snapshots"
```

### Task 7: Sobreposição compacta e posicionamento

**Files:**
- Create: `src/rox_overlay/ui/__init__.py`
- Create: `src/rox_overlay/ui/overlay.py`
- Create: `tests/ui/test_overlay_layout.py`

**Interfaces:**
- Consumes: `OverlaySnapshot`, monitor/área útil e opacidade.
- Produces: `choose_overlay_rect(panel_rect, overlay_size, work_area, offset)`, `OverlayWindow.show_snapshot(snapshot)`, `OverlayWindow.hide_overlay()`, `OverlayWindow.set_opacity(percent)`.

- [ ] **Step 1: Escrever testes falhos do posicionamento**

Cobrir posição 12 px à esquerda, painel na borda esquerda, painel na borda direita, work area de monitor secundário, offsets e garantia de que o overlay permanece totalmente dentro da área útil.

- [ ] **Step 2: Implementar a função pura de posicionamento**

```python
def choose_overlay_rect(panel_rect: Rect, overlay_size: QSize, work_area: Rect, offset: QPoint) -> Rect: ...
```

Preferir esquerda; se não couber, tentar direita, acima e abaixo; por fim limitar à área útil sem cobrir o painel quando houver alternativa.

- [ ] **Step 3: Escrever teste Qt falho da janela**

Com `QT_QPA_PLATFORM=offscreen`, verificar flags always-on-top, frameless, no-focus/click-through, fundo com opacidade configurada e textos atualizados por snapshot.

- [ ] **Step 4: Implementar `OverlayWindow`**

Reproduzir o layout compacto aprovado; manter texto opaco; aplicar opacidade somente ao painel; formatar inteiros com separador de milhar pt-BR; solicitar exclusão da captura via API Windows quando suportada.

- [ ] **Step 5: Executar testes da UI**

Run: `$env:QT_QPA_PLATFORM='offscreen'; python -m pytest tests/ui/test_overlay_layout.py -v`
Expected: PASS para posições, flags, atualização e opacidade.

- [ ] **Step 6: Commit**

```bash
git add src/rox_overlay/ui tests/ui/test_overlay_layout.py
git commit -m "feat: add compact click-through overlay"
```

### Task 8: Configurações, bandeja e composição do aplicativo

**Files:**
- Create: `src/rox_overlay/config.py`
- Create: `src/rox_overlay/ui/settings.py`
- Create: `src/rox_overlay/ui/tray.py`
- Create: `src/rox_overlay/app.py`
- Create: `tests/test_config.py`
- Create: `tests/ui/test_settings.py`
- Create: `tests/test_app_wiring.py`

**Interfaces:**
- Consumes: descoberta/captura/controller/overlay das Tasks 6–7.
- Produces: `AppConfig`, `ConfigStore`, `SettingsWindow`, `TrayController`, `build_application()` e entry point `rox-overlay`.

- [ ] **Step 1: Escrever testes falhos da configuração**

Cobrir padrão preço 0/opacidade 82, limites 25–100, inteiro não negativo, JSON corrompido voltando aos padrões e gravação atômica no diretório local do usuário.

- [ ] **Step 2: Implementar configuração e persistência**

```python
@dataclass(frozen=True) class AppConfig: unit_price: int = 0; opacity_percent: int = 82; window_title_hint: str = ""; offset_x: int = 0; offset_y: int = 0
class ConfigStore:
    def load(self) -> AppConfig: ...
    def save(self, config: AppConfig) -> None: ...
```

- [ ] **Step 3: Escrever testes Qt falhos de configurações/bandeja**

Cobrir lista de janelas, preço, slider 25–100, redetectar, pause/resume, status `Aguardando painel`, salvamento e saída limpa.

- [ ] **Step 4: Implementar `SettingsWindow` e `TrayController`**

Conectar mudanças ao controller/overlay e persistir somente valores validados. A sobreposição permanece click-through; todas as interações ocorrem na janela separada ou bandeja.

- [ ] **Step 5: Escrever o teste falho de composição**

`build_application()` deve construir dependências por interfaces, permitir fakes em teste e garantir `controller.stop()` ao sair.

- [ ] **Step 6: Executar o teste de composição e confirmar falha**

Run: `$env:QT_QPA_PLATFORM='offscreen'; python -m pytest tests/test_app_wiring.py -v`
Expected: FAIL porque `build_application()` ainda não existe.

- [ ] **Step 7: Implementar `build_application()` e o entry point**

Construir dependências por interfaces, conectar encerramento limpo e registrar o comando `rox-overlay` em `pyproject.toml`.

- [ ] **Step 8: Executar testes de configuração e aplicação**

Run: `$env:QT_QPA_PLATFORM='offscreen'; python -m pytest tests/test_config.py tests/ui/test_settings.py tests/test_app_wiring.py -v`
Expected: PASS.

- [ ] **Step 9: Commit**

```bash
git add src/rox_overlay/config.py src/rox_overlay/ui src/rox_overlay/app.py tests
git commit -m "feat: add settings tray and app composition"
```

### Task 9: Diagnóstico explícito, embalagem e validação final

**Files:**
- Create: `scripts/fixture_capture.py`
- Create: `tests/test_fixture_capture.py`
- Create: `packaging/rox-overlay.spec`
- Create: `README.md`
- Modify: `pyproject.toml`

**Interfaces:**
- Consumes: aplicação completa e contratos de captura/pipeline.
- Produces: comando `rox-overlay`, script explícito de captura diagnóstica e ZIP portátil verificável.

- [ ] **Step 1: Escrever teste falho do diagnóstico**

Confirmar que o script não salva nada sem `--output`, remove a imagem após cancelamento e, quando explicitamente solicitado, grava PNG mais JSON com retângulos/confianças sem incluir dados adicionais.

- [ ] **Step 2: Implementar `fixture_capture.py`**

Exigir caminho explícito e uma ação consciente do usuário; nunca habilitar retenção de screenshots por padrão.

- [ ] **Step 3: Configurar a embalagem**

Criar `packaging/rox-overlay.spec` em modo one-folder incluindo plugins Qt necessários, runtime Tesseract, `por/eng.traineddata` e templates. Excluir módulos de desenvolvimento e arquivos de teste.

- [ ] **Step 4: Documentar uso e solução de problemas**

Em `README.md`, cobrir seleção da janela, preço, opacidade, modos suportados, estado `Aguardando painel`, idiomas, privacidade, tela cheia exclusiva best-effort e como gerar uma captura diagnóstica voluntária.

- [ ] **Step 5: Executar toda a suíte**

Run: `python -m pytest -v`
Expected: todos os testes PASS.

- [ ] **Step 6: Executar verificações estáticas**

Run: `python -m compileall -q src scripts`
Expected: exit code 0.

- [ ] **Step 7: Gerar e testar o pacote**

Run: `pyinstaller --clean --noconfirm packaging/rox-overlay.spec`
Expected: `dist/ROX Enchantment Overlay/ROX Enchantment Overlay.exe` e recursos OCR presentes.

Em uma máquina/VM Windows limpa sem Python: abrir o executável, selecionar uma janela, alterar preço/opacidade, abrir/fechar o painel, mover/redimensionar a janela e confirmar que o overlay não captura cliques.

- [ ] **Step 8: Registrar evidências de aceitação**

Adicionar ao README uma matriz curta de Windows/resolução/idioma testados, sem screenshots privadas.

- [ ] **Step 9: Commit**

```bash
git add scripts packaging pyproject.toml README.md tests/test_fixture_capture.py
git commit -m "build: package and document overlay application"
```

### Task 10: Revisão final e release local

**Files:**
- Modify only files identified by review findings.
- Create: `outputs/ROX-Enchantment-Overlay-portable.zip`

**Interfaces:**
- Consumes: todos os artefatos e testes anteriores.
- Produces: pacote portátil final e relatório de verificação.

- [ ] **Step 1: Revisar a implementação contra a especificação**

Comparar cada seção de `docs/superpowers/specs/2026-10-16-rox-enchantment-overlay-design.md` com código e testes; registrar apenas lacunas acionáveis.

- [ ] **Step 2: Corrigir achados e repetir verificações relevantes**

Executar primeiro os testes diretamente afetados e depois `python -m pytest -v`.

- [ ] **Step 3: Produzir o ZIP portátil**

Compactar somente o diretório de distribuição, README e licenças em `outputs/ROX-Enchantment-Overlay-portable.zip`.

- [ ] **Step 4: Verificar o conteúdo do ZIP**

Listar o arquivo sem extrair, confirmar executável, OCR `por/eng`, plugins Qt, README e ausência de testes, caches, configurações pessoais e capturas.

- [ ] **Step 5: Commit de release**

```bash
git add -A
git commit -m "chore: finalize portable overlay release"
```

