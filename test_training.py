import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import joblib
from sklearn.metrics import mean_squared_error, mean_absolute_error
from misr_advanced import MISR_Model
from nuclearpy_models.models.BE.sr_fast import sr_fast_be

# 1. Cargar el dataset
path_train = "Data/Experimental/be_train.csv"
path_test = "Data/Experimental/be_test.csv"
train_df = pd.read_csv(path_train)
test_df = pd.read_csv(path_test)

# 2. Tomar una muestra más representativa (Cientos de núcleos)
# Aumentamos n para que después de filtrar Z [12, 50] sigan quedando muchos puntos
sample_train = train_df
sample_test = test_df

# 3. Configurar el modelo con parámetros balanceados
model = MISR_Model(
    maxiter=10,           
    k_folds=5,           
    population_size= 1000, 
    n_generations= 15,
    s_features= 4  
)

# 4. Ejecutar el entrenamiento
print("Entrenando nuevo modelo MISR con sets explícitos...")
model.fit(sample_train, sample_test)

# Guardar el modelo entrenado
joblib.dump(model, 'misr_model.pkl')
print("Modelo guardado en 'misr_model.pkl'")

# 5. Preparar datos de comparación (Conjunto de Test del modelo)
print("\nGenerando comparativa con el modelo original del paper...")
Y_true = model.Y_test
X_test_features = model.X_test
Extras_test = model.Extras_test # [Z, N]

# Predicciones del nuevo modelo
Y_pred_new = model.predict(pd.DataFrame(X_test_features, columns=model.feature_names))

# Predicciones del modelo del paper
Y_pred_paper = []
for i in range(len(Extras_test)):
    Z, N = Extras_test[i]
    pred, _ = sr_fast_be(Z, N)
    Y_pred_paper.append(pred)
Y_pred_paper = np.array(Y_pred_paper)

# 6. Calcular métricas
def get_metrics(true, pred):
    rmse = np.sqrt(mean_squared_error(true, pred))
    mae = mean_absolute_error(true, pred)
    return rmse, mae

rmse_new, mae_new = get_metrics(Y_true, Y_pred_new)
rmse_paper, mae_paper = get_metrics(Y_true, Y_pred_paper)

print("\n" + "="*40)
print(f"{'Métrica':<15} | {'Nuevo MISR':<12} | {'Paper SR'}")
print("-" * 40)
print(f"{'RMSE':<15} | {rmse_new:<12.4f} | {rmse_paper:.4f}")
print(f"{'MAE':<15} | {mae_new:<12.4f} | {mae_paper:.4f}")
print("="*40)

# Imprimir la expresión completa
print("\nModelo MISR - Expresión Analítica Final:")
print("-" * 40)
print(model.get_formula())
print("-" * 40)

# ─── Métricas adicionales ─────────────────────────────────────────────────────
residuals_new   = Y_true - Y_pred_new
residuals_paper = Y_true - Y_pred_paper
r2_new   = 1 - np.sum(residuals_new**2)   / np.sum((Y_true - Y_true.mean())**2)
r2_paper = 1 - np.sum(residuals_paper**2) / np.sum((Y_true - Y_true.mean())**2)

N_test = Extras_test[:, 1].astype(int)
Z_test = Extras_test[:, 0].astype(int)
A_test = N_test + Z_test
I_test = (N_test - Z_test) / A_test

print(f"\nR²  MISR Nuevo : {r2_new:.4f}")
print(f"R²  Paper SR  : {r2_paper:.4f}")

# ─── 7. Dashboard avanzado ───────────────────────────────────────────────────
from scipy.stats import norm, probplot
from matplotlib.gridspec import GridSpec
from matplotlib.patches import FancyBboxPatch
import matplotlib.colors as mcolors
import matplotlib.ticker as mticker

# ─── Paleta de Colores ────────────────────────────────────────────────────────
BG      = "#0a0e1a"          # Fondo principal (azul marino profundo)
PANEL   = "#0f1525"          # Fondo paneles
GRID    = "#1a2035"          # Líneas de grilla
MISR_C  = "#00e5ff"          # Cyan brillante → MISR Nuevo
PAPER_C = "#ff7043"          # Naranja fuerte  → Paper SR
ZERO_C  = "#ffffff"          # Blanco puro     → líneas de referencia
ACCENT  = "#b388ff"          # Violeta suave   → acentos neutros
TEXT    = "#e0e0e0"

plt.rcParams.update({
    "font.family": "DejaVu Sans",
    "axes.facecolor": PANEL,
    "figure.facecolor": BG,
    "axes.labelcolor": TEXT,
    "xtick.color": "#8b9cbd",
    "ytick.color": "#8b9cbd",
    "axes.edgecolor": "#2d3552",
    "text.color": TEXT,
    "axes.spines.top": False,
    "axes.spines.right": False,
    "axes.grid": True,
    "grid.color": GRID,
    "grid.linewidth": 0.5,
    "legend.framealpha": 0.15,
    "legend.edgecolor": "#3d4a70",
})

# ─── Estructura del Dashboard (4 × 4) ────────────────────────────────────────
fig = plt.figure(figsize=(28, 22), dpi=120, facecolor=BG)
fig.suptitle(
    "MISR vs Paper SR  ─  Nuclear Binding Energy Diagnostic Dashboard",
    fontsize=19, fontweight="bold", color="white", y=1.005,
)
gs = GridSpec(4, 4, figure=fig, hspace=0.48, wspace=0.37)

def _ax(row, col, colspan=1, rowspan=1):
    return fig.add_subplot(gs[row:row+rowspan, col:col+colspan])

# ─── Calcula variables auxiliares ────────────────────────────────────────────
abs_new   = np.abs(residuals_new)
abs_paper = np.abs(residuals_paper)
diff_pred = Y_pred_new - Y_pred_paper      # Diferencia directa entre modelos
avg_pred  = (Y_pred_new + Y_pred_paper) / 2

# ════════════════════════════════════════════════════════════════════════════
# PANEL 1 (0,0)–(0,1): Comparación Directa Modelos: MISR vs Paper SR
# ════════════════════════════════════════════════════════════════════════════
ax = _ax(0, 0, colspan=2)
# Calcular acuerdo entre modelos
rmse_models = np.sqrt(mean_squared_error(Y_pred_paper, Y_pred_new))
r2_models   = 1 - np.sum((Y_pred_new - Y_pred_paper)**2) / np.sum((Y_pred_new - Y_pred_new.mean())**2)

scatter = ax.scatter(Y_pred_paper, Y_pred_new, s=30, c=Y_true, cmap="viridis",
                    alpha=0.8, edgecolors="none", zorder=3)
v_min = min(Y_pred_paper.min(), Y_pred_new.min())
v_max = max(Y_pred_paper.max(), Y_pred_new.max())
ax.plot([v_min, v_max], [v_min, v_max], color=ZERO_C, ls="--", lw=1.8, 
        alpha=0.7, label="Acuerdo Perfecto (y=x)", zorder=4)

ax.set_title("Comparación Directa: MISR Nuevo vs Paper SR", fontweight="bold", fontsize=14)
ax.set_xlabel("Predicción Paper SR (MeV)", fontsize=11)
ax.set_ylabel("Predicción MISR Nuevo (MeV)", fontsize=11)

# Barra de color para contexto de energía real
cbar = plt.colorbar(scatter, ax=ax, pad=0.02)
cbar.set_label("BE Experimental (MeV)", fontsize=9)

ax.legend([f"RMSD Modelos: {rmse_models:.3f} MeV", f"R² Acuerdo: {r2_models:.4f}"], 
          fontsize=10, loc="upper left", facecolor=BG, edgecolor=GRID)

# ════════════════════════════════════════════════════════════════════════════
# PANEL 2 (0,2): Distribución de Residuos (Histograma superpuesto)
# ════════════════════════════════════════════════════════════════════════════
ax = _ax(0, 2)
for res, c, lbl in [(residuals_new, MISR_C, "MISR Nuevo"),
                    (residuals_paper, PAPER_C, "Paper SR")]:
    mu, sig = np.mean(res), np.std(res)
    ax.hist(res, bins=32, alpha=0.35, color=c, density=True, label=lbl)
    xs = np.linspace(min(res.min(), -3*sig), max(res.max(), 3*sig), 300)
    ax.plot(xs, norm.pdf(xs, mu, sig), color=c, lw=2.2,
            label=f"{lbl}\nμ={mu:+.2f}  σ={sig:.2f}")
ax.axvline(0, color=ZERO_C, ls="--", lw=1.3, alpha=0.7, label="Zero")
ax.set_title("Distribución de Residuos", fontweight="bold", fontsize=12)
ax.set_xlabel("Error (MeV)"); ax.set_ylabel("Densidad")
ax.legend(fontsize=7.5)

# ════════════════════════════════════════════════════════════════════════════
# PANEL 3 (0,3): Q-Q Plot (Normalidad del Error MISR)
# ════════════════════════════════════════════════════════════════════════════
ax = _ax(0, 3)
(osm_n, osr_n), (sl_n, ic_n, _) = probplot(residuals_new,   dist="norm")
(osm_p, osr_p), (sl_p, ic_p, _) = probplot(residuals_paper, dist="norm")
ax.scatter(osm_n, osr_n, s=14, color=MISR_C,  alpha=0.75, edgecolors="none",
           label="MISR Nuevo")
ax.scatter(osm_p, osr_p, s=9,  color=PAPER_C, alpha=0.50, edgecolors="none",
           label="Paper SR")
ref = np.array([min(osm_n.min(), osm_p.min()), max(osm_n.max(), osm_p.max())])
ax.plot(ref, sl_n * ref + ic_n, color=MISR_C,  ls="--", lw=1.4, alpha=0.8)
ax.plot(ref, sl_p * ref + ic_p, color=PAPER_C, ls="--", lw=1.4, alpha=0.8)
ax.set_title("Q-Q Plot — Normalidad del Error", fontweight="bold", fontsize=12)
ax.set_xlabel("Cuantil Teórico"); ax.set_ylabel("Cuantil Observado")
ax.legend(fontsize=9)

# ════════════════════════════════════════════════════════════════════════════
# PANEL 4 (1,0): Residuo vs Masa Atómica A
# ════════════════════════════════════════════════════════════════════════════
ax = _ax(1, 0)
ax.scatter(A_test, residuals_new,   s=18, alpha=0.65, color=MISR_C,
           edgecolors="none", label="MISR Nuevo")
ax.scatter(A_test, residuals_paper, s=12, alpha=0.40, color=PAPER_C,
           edgecolors="none", label="Paper SR")
ax.axhline(0, color=ZERO_C, ls="--", lw=1.2, alpha=0.6)
# Banda ±1 MeV
ax.fill_between([A_test.min(), A_test.max()], -1, 1,
                color=ACCENT, alpha=0.12, label="Banda ±1 MeV")
ax.set_title("Residuo vs Masa Atómica (A)", fontweight="bold", fontsize=12)
ax.set_xlabel("A  (Nucleones totales)"); ax.set_ylabel("Residuo (MeV)")
ax.legend(fontsize=8.5)

# ════════════════════════════════════════════════════════════════════════════
# PANEL 5 (1,1): Residuo vs Número Atómico Z
# ════════════════════════════════════════════════════════════════════════════
ax = _ax(1, 1)
ax.scatter(Z_test, residuals_new,   s=18, alpha=0.65, color=MISR_C,
           edgecolors="none", label="MISR Nuevo")
ax.scatter(Z_test, residuals_paper, s=12, alpha=0.40, color=PAPER_C,
           edgecolors="none", label="Paper SR")
ax.axhline(0, color=ZERO_C, ls="--", lw=1.2, alpha=0.6)
ax.fill_between([Z_test.min(), Z_test.max()], -1, 1,
                color=ACCENT, alpha=0.12)
# Marcar números mágicos
for zm in [20, 28, 50]:
    if Z_test.min() <= zm <= Z_test.max():
        ax.axvline(zm, color="#ffd740", ls=":", lw=1.2, alpha=0.6)
ax.set_title("Residuo vs Número Atómico (Z)", fontweight="bold", fontsize=12)
ax.set_xlabel("Z  (Protones)"); ax.set_ylabel("Residuo (MeV)")
ax.legend(fontsize=8.5)

# ════════════════════════════════════════════════════════════════════════════
# PANEL 6 (1,2): Residuo vs Número de Neutrones N
# ════════════════════════════════════════════════════════════════════════════
ax = _ax(1, 2)
ax.scatter(N_test, residuals_new,   s=18, alpha=0.65, color=MISR_C,
           edgecolors="none", label="MISR Nuevo")
ax.scatter(N_test, residuals_paper, s=12, alpha=0.40, color=PAPER_C,
           edgecolors="none", label="Paper SR")
ax.axhline(0, color=ZERO_C, ls="--", lw=1.2, alpha=0.6)
for nm in [20, 28, 50]:
    if N_test.min() <= nm <= N_test.max():
        ax.axvline(nm, color="#ffd740", ls=":", lw=1.2, alpha=0.6,
                   label=f"N={nm}")
ax.set_title("Residuo vs Número de Neutrones (N)", fontweight="bold", fontsize=12)
ax.set_xlabel("N  (Neutrones)"); ax.set_ylabel("Residuo (MeV)")
ax.legend(fontsize=8)

# ════════════════════════════════════════════════════════════════════════════
# PANEL 7 (1,3): Residuo vs Asimetría I
# ════════════════════════════════════════════════════════════════════════════
ax = _ax(1, 3)
ax.scatter(I_test, residuals_new,   s=18, alpha=0.65, color=MISR_C,
           edgecolors="none", label="MISR Nuevo")
ax.scatter(I_test, residuals_paper, s=12, alpha=0.40, color=PAPER_C,
           edgecolors="none", label="Paper SR")
ax.axhline(0, color=ZERO_C, ls="--", lw=1.2, alpha=0.6)
# Ajuste lineal de tendencia sobre los residuos
for res, c in [(residuals_new, MISR_C), (residuals_paper, PAPER_C)]:
    z  = np.polyfit(I_test, res, 1)
    pf = np.poly1d(z)
    xs = np.linspace(I_test.min(), I_test.max(), 200)
    ax.plot(xs, pf(xs), color=c, lw=2, ls="-", alpha=0.9)
ax.set_title("Residuo vs Asimetría de Isospín (I)", fontweight="bold", fontsize=12)
ax.set_xlabel("I = (N−Z)/A"); ax.set_ylabel("Residuo (MeV)")
ax.legend(fontsize=8.5)

# ════════════════════════════════════════════════════════════════════════════
# PANEL 8 (2,0)–(2,1): Bland-Altman — Concordancia entre modelos
# ════════════════════════════════════════════════════════════════════════════
ax = _ax(2, 0, colspan=2)
ba_mean = avg_pred
ba_diff = diff_pred
mu_ba   = np.mean(ba_diff)
sd_ba   = np.std(ba_diff)
ax.scatter(ba_mean, ba_diff, s=18, alpha=0.60, color=ACCENT, edgecolors="none",
           label="MISR Nuevo − Paper SR")
ax.axhline(mu_ba,          color=ZERO_C, lw=1.6, ls="-",  label=f"Sesgo = {mu_ba:+.3f} MeV")
ax.axhline(mu_ba + 1.96*sd_ba, color=MISR_C, lw=1.4, ls="--",
           label=f"LSD+1.96σ = {mu_ba+1.96*sd_ba:+.2f}")
ax.axhline(mu_ba - 1.96*sd_ba, color=PAPER_C, lw=1.4, ls="--",
           label=f"LSD−1.96σ = {mu_ba-1.96*sd_ba:+.2f}")
ax.fill_between([ba_mean.min(), ba_mean.max()],
                mu_ba - 1.96*sd_ba, mu_ba + 1.96*sd_ba,
                color=ACCENT, alpha=0.07)
ax.set_title("Bland-Altman — Concordancia MISR vs Paper SR", fontweight="bold", fontsize=12)
ax.set_xlabel("Predicción Media (MeV)"); ax.set_ylabel("Diferencia: MISR − Paper (MeV)")
ax.legend(fontsize=8.5)

# ════════════════════════════════════════════════════════════════════════════
# PANEL 9 (2,2): CDF del Error Absoluto
# ════════════════════════════════════════════════════════════════════════════
ax = _ax(2, 2)
for res, c, lbl in [(abs_new, MISR_C, "MISR Nuevo"),
                    (abs_paper, PAPER_C, "Paper SR")]:
    srt = np.sort(res)
    cdf = np.arange(1, len(srt)+1) / len(srt)
    ax.plot(srt, cdf, color=c, lw=2.5, label=lbl)
    med = np.median(res)
    ax.axvline(med, color=c, ls=":", lw=1.4, alpha=0.8,
               label=f"Mediana {lbl}: {med:.2f}")
ax.axhline(0.50, color=ZERO_C, ls="--", lw=0.9, alpha=0.4)
ax.axhline(0.90, color="#ffd740", ls="--", lw=0.9, alpha=0.4, label="P90")
ax.set_title("CDF del Error Absoluto", fontweight="bold", fontsize=12)
ax.set_xlabel("|Error| (MeV)"); ax.set_ylabel("Fracción Acumulada")
ax.legend(fontsize=7.5)

# ════════════════════════════════════════════════════════════════════════════
# PANEL 10 (2,3): Violin / Box de los |Residuos| por modelo
# ════════════════════════════════════════════════════════════════════════════
ax = _ax(2, 3)
vp = ax.violinplot([abs_new, abs_paper], positions=[1, 2],
                   showmedians=True, showextrema=True, widths=0.6)
vp['cmedians'].set_color(ZERO_C);   vp['cmedians'].set_linewidth(2)
vp['cmaxes'].set_color(ZERO_C);     vp['cmins'].set_color(ZERO_C)
vp['cbars'].set_color(ZERO_C)
if hasattr(vp, 'bodies'):
    vp['bodies'][0].set_facecolor(MISR_C);  vp['bodies'][0].set_alpha(0.5)
    vp['bodies'][1].set_facecolor(PAPER_C); vp['bodies'][1].set_alpha(0.4)
else:
    for body in vp['bodies']:
        body.set_alpha(0.4)
ax.set_xticks([1, 2])
ax.set_xticklabels(["MISR Nuevo", "Paper SR"], fontsize=10)
ax.set_title("Distribución Violin de |Error|", fontweight="bold", fontsize=12)
ax.set_ylabel("|Residuo| (MeV)")

# ════════════════════════════════════════════════════════════════════════════
# PANEL 11 (3,0): Importancia de Características
# ════════════════════════════════════════════════════════════════════════════
ax = _ax(3, 0)
try:
    feats = model.feature_names
    imps  = np.array(model.feature_importances_, dtype=float)
    imps  = imps / imps.sum() if imps.sum() > 0 else imps
    idx   = np.argsort(imps)
    cmap  = plt.cm.cool(np.linspace(0.3, 1.0, len(feats)))
    bars  = ax.barh(np.arange(len(feats)), imps[idx], color=cmap, alpha=0.88, height=0.65)
    ax.set_yticks(np.arange(len(feats)))
    ax.set_yticklabels([feats[i] for i in idx], fontsize=11, fontweight="bold")
    # Etiquetas de valor
    for bar, val in zip(bars, imps[idx]):
        ax.text(bar.get_width() + 0.003, bar.get_y() + bar.get_height()/2,
                f"{val:.3f}", va="center", fontsize=8.5, color=TEXT)
    ax.set_title("Importancia de Características (BDT + MI)", fontweight="bold", fontsize=12)
    ax.set_xlabel("Probabilidad de Selección (normalizada)")
except Exception as e:
    ax.text(0.5, 0.5, f"No disp:\n{e}", ha="center", va="center", transform=ax.transAxes)

# ════════════════════════════════════════════════════════════════════════════
# PANEL 12 (3,1): Error Acumulado (Running RMSE) por A creciente
# ════════════════════════════════════════════════════════════════════════════
ax = _ax(3, 1)
sort_idx = np.argsort(A_test)
A_sorted = A_test[sort_idx]
for res, c, lbl in [(residuals_new[sort_idx], MISR_C, "MISR Nuevo"),
                    (residuals_paper[sort_idx], PAPER_C, "Paper SR")]:
    run_rmse = [np.sqrt(np.mean(res[:k+1]**2)) for k in range(1, len(res)+1)]
    ax.plot(A_sorted, run_rmse, color=c, lw=2, label=lbl, alpha=0.9)
ax.set_title("RMSE Acumulado (orden A creciente)", fontweight="bold", fontsize=12)
ax.set_xlabel("Masa Atómica A"); ax.set_ylabel("RMSE Acumulado (MeV)")
ax.legend(fontsize=9)

# ════════════════════════════════════════════════════════════════════════════
# PANEL 13 (3,2): Percentiles de Error por banda de A
# ════════════════════════════════════════════════════════════════════════════
ax = _ax(3, 2)
bins_A = np.arange(A_test.min(), A_test.max()+20, 20)
bin_centers = 0.5 * (bins_A[:-1] + bins_A[1:])
med_new   = []; med_pap = []
p25_new   = []; p75_new = []
p25_pap   = []; p75_pap = []
for lo_b, hi_b in zip(bins_A[:-1], bins_A[1:]):
    mask = (A_test >= lo_b) & (A_test < hi_b)
    if mask.sum() < 2:
        for lst in [med_new, med_pap, p25_new, p75_new, p25_pap, p75_pap]:
            lst.append(np.nan)
        continue
    rn, rp = abs_new[mask], abs_paper[mask]
    med_new.append(np.median(rn)); p25_new.append(np.percentile(rn, 25)); p75_new.append(np.percentile(rn, 75))
    med_pap.append(np.median(rp)); p25_pap.append(np.percentile(rp, 25)); p75_pap.append(np.percentile(rp, 75))

bc = np.array(bin_centers); mn = np.array(med_new); mp = np.array(med_pap)
ax.plot(bc, mn, color=MISR_C,  lw=2, marker="o", ms=5, label="MISR Nuevo (mediana)")
ax.fill_between(bc, np.array(p25_new), np.array(p75_new), color=MISR_C, alpha=0.18)
ax.plot(bc, mp, color=PAPER_C, lw=2, marker="s", ms=5, label="Paper SR (mediana)")
ax.fill_between(bc, np.array(p25_pap), np.array(p75_pap), color=PAPER_C, alpha=0.18)
ax.set_title("|Error| por Banda de Masa (±IQR)", fontweight="bold", fontsize=12)
ax.set_xlabel("Masa Atómica A  (bin de 20)"); ax.set_ylabel("|Error| Mediano (MeV)")
ax.legend(fontsize=8.5)

# ════════════════════════════════════════════════════════════════════════════
# PANEL 14 (3,3): Tabla de Estadísticas Completa
# ════════════════════════════════════════════════════════════════════════════
ax = _ax(3, 3)
ax.axis("off")
p90_n  = np.percentile(abs_new, 90);  p90_p  = np.percentile(abs_paper, 90)
p95_n  = np.percentile(abs_new, 95);  p95_p  = np.percentile(abs_paper, 95)
win_pct = (abs_new < abs_paper).mean() * 100  # % veces MISR gana al Paper
table_data = [
    ["Estadístico",      "MISR Nuevo",                               "Paper SR"],
    ["RMSE (MeV)",       f"{rmse_new:.4f}",                          f"{rmse_paper:.4f}"],
    ["MAE  (MeV)",       f"{mae_new:.4f}",                           f"{mae_paper:.4f}"],
    ["R²",               f"{r2_new:.5f}",                            f"{r2_paper:.5f}"],
    ["Sesgo μ (MeV)",    f"{residuals_new.mean():+.4f}",             f"{residuals_paper.mean():+.4f}"],
    ["Std Error σ",      f"{residuals_new.std():.4f}",               f"{residuals_paper.std():.4f}"],
    ["Mediana |e| ",     f"{np.median(abs_new):.4f}",                f"{np.median(abs_paper):.4f}"],
    ["Perc 90 |e|",      f"{p90_n:.4f}",                             f"{p90_p:.4f}"],
    ["Perc 95 |e|",      f"{p95_n:.4f}",                             f"{p95_p:.4f}"],
    ["Max |Error|",      f"{abs_new.max():.2f}",                     f"{abs_paper.max():.2f}"],
    ["MISR gana en",     f"{win_pct:.1f}% de núcleos",               "—"],
    ["Núcleos test",     str(len(Y_true)),                            str(len(Y_true))],
]
tbl = ax.table(cellText=table_data, loc="center", cellLoc="center", edges="horizontal")
tbl.auto_set_font_size(False)
tbl.set_fontsize(9.5)
tbl.scale(1.1, 1.85)
# Encabezado
for col in range(3):
    cell = tbl[(0, col)]
    cell.set_facecolor("#1a2f6e")
    cell.set_text_props(color="white", fontweight="bold")
# Colorear mejor resultado en cada métrica
metrics_better_low = [1, 2, 4, 5, 6, 7, 8, 9]  # filas donde "menor es mejor"
for row_i in metrics_better_low:
    try:
        v_misr  = float(table_data[row_i][1].replace("+",""))
        v_paper = float(table_data[row_i][2].replace("+",""))
        better_col = 1 if abs(v_misr) <= abs(v_paper) else 2
        tbl[(row_i, better_col)].set_facecolor("#0a3320")
        tbl[(row_i, better_col)].set_text_props(color="#00e5a0", fontweight="bold")
    except Exception:
        pass
ax.set_title("Resumen Estadístico Completo", fontsize=12, fontweight="bold", pad=20)

# ─── Exportar ─────────────────────────────────────────────────────────────────
plt.tight_layout()
out = "comparison_test_detailed.png"
plt.savefig(out, facecolor=BG, dpi=130, bbox_inches="tight")
print(f"\nDashboard guardado como '{out}'")




