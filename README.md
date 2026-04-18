# 📺 Persona 4 Data Explorer

[![Ask DeepWiki](https://devin.ai/assets/askdeepwiki.png)](https://deepwiki.com/jpmasangkay/smt-data-visualization)

### Midnight District Interactive Visualizer

**Explore. Analyze. Synthesize. Now.**

An interactive data visualization application for Shin Megami Tensei: Persona 4 — featuring a custom isometric 3D renderer, 12 unique interactive data buildings, real-time procedural city maps, and complex 3D chart rendering, all wrapped in a sleek Midnight Channel aesthetic.

[![Python](https://img.shields.io/badge/Python-3-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://www.python.org/)
[![Pygame-CE](https://img.shields.io/badge/Pygame--CE-2.5.0-F2FF00?style=for-the-badge&logo=python&logoColor=black)](https://pyga.me/)
[![Matplotlib](https://img.shields.io/badge/Matplotlib-3.7.0-11557c?style=for-the-badge&logo=python&logoColor=white)](https://matplotlib.org/)
[![Pandas](https://img.shields.io/badge/Pandas-2.0.0-150458?style=for-the-badge&logo=pandas&logoColor=white)](https://pandas.pydata.org/)
[![NumPy](https://img.shields.io/badge/NumPy-1.24.0-013243?style=for-the-badge&logo=numpy&logoColor=white)](https://numpy.org/)

---

## ✨ Features

### 🏙️ Isometric City Exploration

- **Custom Isometric Renderer** — navigate the "Midnight District" using an interactive 3D camera
- **Depth-sorted Rendering Pipeline** — seamless interleaving of static procedural map tiles and animated assets
- **Animated Sprites** — custom-animated sprite sheets for locations like the *Velvet Room* and *Junes Mall* 

### 📊 Interactive Data Visualization

- **12 Interactive Buildings** — locations like the *Block Fortress*, *Skill Arcade*, *Shadow Den*, and *Inheritance Lab* serve as nodes for data discovery
- **Seamless Matplotlib 3D Charts** — each building generates distinct 3D charts (scatter clouds, grouped bars, networks, surface heatmaps) 
- **Synchronized Coordinate Mapping** — perfect spatial and rotational alignment between the zero-lag Pygame renderer and static Matplotlib charts

### ⚡ Performance & UX

- **Zero-lag Rendering** — highly optimized rendering loop utilizing Pygame-CE
- **Dynamic HUD** — fully responsive heads-up display, procedural minimaps, and real-time status bars
- **Midnight Channel Aesthetics** — strict adherence to Persona 4's neon-accented, dark interface style (vibrant yellows, deep purples, TV static)

---

## 🛠️ Tech Stack

### Core Technologies

| Technology | Purpose |
|-----------|---------|
| **Python 3** | Core language for logic, data processing, and rendering |
| **Pygame-CE** | High-performance visual rendering, window management, and input handling |
| **Matplotlib** | Generating complex 3D charts, scatter plots, and network graphs |
| **Pandas** | Loading, merging, and cleaning complex CSV data of Persona skills and stats |
| **NumPy** | Matrix math, transformations, and coordinate alignment for the 3D space |

---

## 🚀 Getting Started

### Prerequisites

- [Python](https://www.python.org/downloads/) 3.9+
- Pip package manager

### Installation

```bash
# Clone the repository
git clone https://github.com/jpmasangkay/smt-data-visualization.git
cd smt-data-visualization

# Install dependencies
pip install -r requirements.txt
```

### Development & Execution

```bash
# Run the application
python main.py
```

---

## 📁 Project Structure

```
smt-data-visualization/
├── src/                             # Modular source package
│   ├── __init__.py                  # Package init
│   ├── constants.py                 # Colors, dimensions, building definitions
│   ├── data_loader.py               # CSV data loading
│   ├── world.py                     # Isometric projection & building renderer
│   ├── renderer.py                  # Fast software 3D chart engine
│   ├── charts.py                    # 12 matplotlib chart renderers
│   ├── scenes.py                    # 12 fast 3D scene builders
│   ├── entities.py                  # Player, Camera, particle systems
│   └── game.py                      # Main Game class with all logic
├── data/                            # Datasets for visualization
│   ├── personas.csv                 # Core stats and levels
│   ├── skills.csv                   # Skill costs and elements
│   ├── skill_connection.csv         # Network relationships between Personas and Skills
│   └── c_*.csv                      # Affinities (weak, resist, block, etc.)
├── assets/                          # Sprites and visual assets
│   ├── characters/                  # Character sprite sheets
│   └── buildings/                   # Velvet Room, Junes Mall animated sprites
├── main.py                          # Application entry point
├── requirements.txt                 # Project module dependencies
└── README.md                        # Documentation
```

---

## 🧠 How It Works

This project fuses game engine techniques with data science visualization:

1. **Data Ingestion** — `pandas` is used to load and relate large CSV datasets mapping over hundreds of Personas, their skills, arcana, base stats, and elemental affinities.
2. **Procedural City Generation** — An algorithm populates the "Midnight District" with interactive charting locations, ambient skyscrapers, walkways, and streetlamps.
3. **Optimized 3D Engine** — `Pygame-CE` handles an isometric projection math pipeline. As the user pans and rotates the camera, matrices multiply to accurately draw the tile-based world.
4. **On-Demand Matplotlib** — When a user interacts with a building, `matplotlib` calculates and draws complex 3D graphs (e.g., surface plots, scatter clouds) within Python memory.
5. **Buffer Conversion** — Matplotlib outputs an RGBA buffer which is converted directly back into Pygame surfaces. These surfaces are layered into the 3D scene in zero-lag real time, matching the current user-controlled camera elevation and azimuth perfectly.

---

## 👥 Team

| Role | Responsibility |
|------|---------------|
| **Lead Developer** | Architecture, 3D logic, Engine integration |
| **Data Analyst** | CSV structuring, Matplotlib charting logic |
| **UI/UX Designer** | Midnight District aesthetic, Sprite direction |

---

## 👏 Acknowledgements

- Visual aesthetics inspired by [ATLUS - Persona 4](https://atlus.com/p4g/)
- Enhanced rendering pipeline via [Pygame-Community Edition](https://pyga.me/)
- Data charting powered by [Matplotlib](https://matplotlib.org/)

---
