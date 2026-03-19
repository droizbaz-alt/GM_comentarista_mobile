# ♟️ Manual de Usuario: GM Comentarista Mobile

Bienvenidos a **GM Comentarista**, una aplicación web progresiva (PWA) diseñada para ofrecer un análisis pedagógico de partidas de ajedrez a nivel de Gran Maestro, optimizada tanto para escritorio como para dispositivos móviles.

Este manual detalla todas las funcionalidades de la aplicación para que puedas sacar el máximo provecho de tus análisis.

---

## 📅 Índice
1. [Introducción y Conceptos Básicos](#1-introducción-y-conceptos-básicos)
2. [Configuración Inicial (Motor e IA)](#2-configuración-inicial-motor-e-ia)
3. [Cargar una Partida](#3-cargar-una-partida)
4. [Análisis de la Partida](#4-análisis-de-la-partida)
5. [Visor Interactivo y Resultados](#5-visor-interactivo-y-resultados)
6. [Gestión e Historial](#6-gestión-e-historial)

---

## 1. Introducción y Conceptos Básicos

**GM Comentarista** combina la precisión absoluta del motor de ajedrez líder (Stockfish) con la capacidad de explicación pedagógica de los modelos de inteligencia artificial de Google (Gemini y Gemma). 
La aplicación evalúa tus partidas, detecta los momentos críticos y utiliza la IA para explicarte *por qué* un movimiento es bueno, malo o dudoso, como si tuvieras a un entrenador personal a tu lado.

---

## 2. Configuración Inicial (Motor e IA)

Antes de analizar tu primera partida, despliega el panel **⚙️ Configuración** para ajustar el comportamiento de la app:

### Perfiles de Análisis
Tienes tres perfiles predefinidos que balancean velocidad y profundidad:
- ⚡ **Rápido:** Ideal para partidas Blitz. Análisis ligero (Profundidad 12) usando modelos IA básicos.
- ⚖️ **Estándar (Recomendado):** El equilibrio perfecto. Buena profundidad (16) detectando errores serios.
- 🏆 **Profundo:** Para partidas de torneo o ritmos clásicos. Usa evaluación exhaustiva (Profundidad 20) y los modelos Pro de IA para un nivel de detalle excepcional.

### Ajustes de IA (Gemini)
- **API Key:** Si no está configurada automáticamente en el servidor, deberás introducir tu clave gratuita de Google AI Studio.
- **Modo Híbrido:** Si está activo (recomendado), la app usará modelos súper veloces (Flash-lite) para jugadas normales, y reservará los modelos inteligentes (Pro) para explicar los errores graves o momentos críticos de la partida.
- **Caché:** Guarda los análisis de posiciones ya calculadas para no gastar cuota de API en caso de re-análisis. (Puedes limpiar la caché en cualquier momento).

### Ajustes Avanzados
Podrás personalizar exactamente cuántos hilos de tu procesador usar y qué umbral (ventaja en peones) considerar como "crítico" para alertar a la IA. También permite seleccionar manualmente qué modelo de IA usar para cada caso.

---

## 3. Cargar una Partida

Dirígete a la sección **📥 Cargar Partida**. Encontrarás 4 pestañas según el origen de tu partida:

1. **📂 Archivo PGN:** Sube cualquier archivo `.pgn` clásico que tengas en tu ordenador o móvil.
2. **🔗 Lichess:** Introduce tu nombre de usuario de Lichess (para buscar tus partidas más recientes) o el ID directo de una partida concreta (ej: `abc12345`). La app la descargará automáticamente.
3. **📋 Historial:** Recupera partidas que ya hayas analizado en el pasado y que estén guardadas en la memoria de la app.
4. **✏️ Crear:** Si no tienes el texto, usa el tablero interactivo para mover las piezas y reproducir la partida que quieres analizar jugada a jugada.

---

## 4. Análisis de la Partida

Una vez cargada la partida mediante cualquiera de los métodos anteriores y confirmada en el panel (verás un aviso de `✅ Partida cargada — lista para analizar`), tan solo tienes que pulsar el botón azul:

**🚀 Generar Comentarios**

1. La barra de progreso te indicará cuántas jugadas ha procesado Stockfish.
2. Luego indicará que está conectando con la IA para redactar los textos.
3. El proceso puede durar desde escasos segundos hasta un par de minutos dependiendo del "Perfil de Análisis" escogido.

---

## 5. Visor Interactivo y Resultados

Una vez completado el análisis, se desplegará el **Visor de Ajedrez**:

- **Navegación Táctil:** Usa los grandes botones `⏮` (Inicio), `◀` (Atrás), `▶` (Adelante) y `⏭` (Final) o desliza el Slider para viajar por las jugadas.
- **Comentarios en vivo:** Debajo del tablero verás el comentario del Gran Maestro (IA) específico para la posición actual en la que te encuentras. Te explicará planes, celadas o el porqué de un error.
- **Variantes Recomendadas:** Si hiciste un error grave, la pantalla te alertará con un aviso amarillo `⚠️ Variantes disponibles en esta posición`. Haciendo clic en esos botones, la app ejecutará la línea que el motor sugería como la jugada correcta.
- **📜 Crónica completa:** Despliega este menú para ver un resumen en formato lista de texto con todas las jugadas y sus comentarios sin mover piezas.

---

## 6. Gestión e Historial

Al final de la pantalla tienes la opción de conservar tu trabajo:
- Puedes ver el PGN en crudo haciendo clic en "Ver PGN completo".
- **📥 Descargar PGN Comentado:** Haz clic para guardar el archivo `.pgn` en tu dispositivo. Este archivo ahora contiene la partida original MÁS los comentarios de la IA, por lo que podrás abrirlo en ChessBase, Lichess, o cualquier programa de ajedrez estándar conservando las explicaciones.
- Pulsa `🔄 Nueva partida` para limpiar la pantalla y comenzar otra sesión de estudio.
