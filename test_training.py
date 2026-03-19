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
    maxiter=5,           
    k_folds=5,           
    population_size= 600, 
    n_generations= 10,
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

# ─── 7. Dashboard 3×3 ────────────────────────────────────────────────────────
from scipy.stats import norm, probplot

BG = "#0d1117"; C1 = "#00f2fe"; C2 = "#f9d423"; CGRD = "#21262d"

plt.rcParams.update({
    "font.family": "DejaVu Sans", "axes.facecolor": "#161b22",
    "figure.facecolor": BG, "axes.labelcolor": "#c9d1d9",
    "xtick.color": "#8b949e", "ytick.color": "#8b949e",
    "axes.edgecolor": "#30363d", "text.color": "#c9d1d9",
    "axes.spines.top": False, "axes.spines.right": False,
})

fig, axes = plt.subplots(3, 3, figsize=(21, 15), dpi=110)
fig.suptitle("MISR Nuclear Binding Energy — Diagnostic Dashboard",
             fontsize=17, fontweight="bold", color="white", y=1.01)
axes = axes.flatten()

# ── 1. Real vs Predicho ──────────────────────────────────────────────────────
ax = axes[0]
ax.scatter(Y_true, Y_pred_new,   s=22, alpha=0.65, color=C1, edgecolors="none",
           label=f"MISR Nuevo  R²={r2_new:.3f}  RMSE={rmse_new:.2f}")
ax.scatter(Y_true, Y_pred_paper, s=14, alpha=0.30, color=C2, edgecolors="none",
           label=f"Paper SR    R²={r2_paper:.3f}  RMSE={rmse_paper:.2f}")
lo, hi = Y_true.min(), Y_true.max()
ax.plot([lo, hi], [lo, hi], "r--", lw=1.4, alpha=0.8)
ax.set_title("Correlación: Real vs Predicho", fontweight="bold")
ax.set_xlabel("BE Experimental (MeV)"); ax.set_ylabel("BE Predicho (MeV)")
ax.legend(fontsize=8.5); ax.grid(True, color=CGRD, linewidth=0.5)

# ── 2. Distribución de Residuos + Gaussiana ajustada ─────────────────────────
ax = axes[1]
for res, color, lbl in [(residuals_new, C1, "MISR Nuevo"), (residuals_paper, C2, "Paper SR")]:
    ax.hist(res, bins=28, alpha=0.45, color=color, density=True, label=lbl)
    mu, sigma = np.mean(res), np.std(res)
    xs = np.linspace(res.min(), res.max(), 200)
    ax.plot(xs, norm.pdf(xs, mu, sigma), color=color, lw=2, label=f"{lbl} μ={mu:.2f} σ={sigma:.2f}")
ax.axvline(0, color="white", ls="--", alpha=0.4)
ax.set_title("Residuos + Gaussiana Ajustada", fontweight="bold")
ax.set_xlabel("Error (MeV)"); ax.set_ylabel("Densidad")
ax.legend(fontsize=8); ax.grid(True, color=CGRD, linewidth=0.5)

# ── 3. QQ-Plot (normalidad del error MISR) ────────────────────────────────────
ax = axes[2]
(osm, osr), (slope, intercept, _) = probplot(residuals_new, dist="norm")
ax.scatter(osm, osr, s=16, color=C1, alpha=0.75, edgecolors="none", label="MISR Nuevo")
ref = np.array([osm.min(), osm.max()])
ax.plot(ref, slope * ref + intercept, "r--", lw=1.5, label="Normal ideal")
ax.set_title("Q-Q Plot — Normalidad del Error", fontweight="bold")
ax.set_xlabel("Cuantil Teórico"); ax.set_ylabel("Cuantil Observado")
ax.legend(fontsize=9); ax.grid(True, color=CGRD, linewidth=0.5)

# ── 4. Error vs Masa Atómica A ───────────────────────────────────────────────
ax = axes[3]
ax.scatter(A_test, residuals_new,   s=20, alpha=0.65, color=C1, edgecolors="none", label="MISR")
ax.scatter(A_test, residuals_paper, s=14, alpha=0.30, color=C2, edgecolors="none", label="Paper SR")
ax.axhline(0, color="red", ls="--", lw=1, alpha=0.6)
ax.set_title("Residuo vs Masa Atómica (A)", fontweight="bold")
ax.set_xlabel("A (Nucleones)"); ax.set_ylabel("Residuo (MeV)")
ax.legend(fontsize=9); ax.grid(True, color=CGRD, linewidth=0.5)

# ── 5. Error vs Número Atómico Z ─────────────────────────────────────────────
ax = axes[4]
ax.scatter(Z_test, residuals_new,   s=20, alpha=0.65, color=C1, edgecolors="none", label="MISR")
ax.scatter(Z_test, residuals_paper, s=14, alpha=0.30, color=C2, edgecolors="none", label="Paper SR")
ax.axhline(0, color="red", ls="--", lw=1, alpha=0.6)
ax.set_title("Residuo vs Número Atómico (Z)", fontweight="bold")
ax.set_xlabel("Z (Protones)"); ax.set_ylabel("Residuo (MeV)")
ax.legend(fontsize=9); ax.grid(True, color=CGRD, linewidth=0.5)

# ── 6. Error vs Asimetría de Isospín I ───────────────────────────────────────
ax = axes[5]
ax.scatter(I_test, residuals_new,   s=20, alpha=0.65, color=C1, edgecolors="none", label="MISR")
ax.scatter(I_test, residuals_paper, s=14, alpha=0.30, color=C2, edgecolors="none", label="Paper SR")
ax.axhline(0, color="red", ls="--", lw=1, alpha=0.6)
ax.set_title("Residuo vs Asimetría de Isospín (I)", fontweight="bold")
ax.set_xlabel("I = (N−Z)/A"); ax.set_ylabel("Residuo (MeV)")
ax.legend(fontsize=9); ax.grid(True, color=CGRD, linewidth=0.5)

# ── 7. Importancia de Características ────────────────────────────────────────
ax = axes[6]
try:
    feats = model.feature_names
    imps  = np.array(model.feature_importances_, dtype=float)
    imps  = imps / imps.sum() if imps.sum() > 0 else imps
    idx   = np.argsort(imps)
    cmap  = plt.cm.Blues(np.linspace(0.4, 0.9, len(feats)))
    ax.barh(np.arange(len(feats)), imps[idx], color=cmap, alpha=0.85)
    ax.set_yticks(np.arange(len(feats)))
    ax.set_yticklabels([feats[i] for i in idx], fontsize=11)
    ax.set_title("Importancia de Características (MI)", fontweight="bold")
    ax.set_xlabel("Prob. Selección Normalizada")
    ax.grid(axis="x", color=CGRD, linewidth=0.5)
except Exception as e:
    ax.text(0.5, 0.5, f"No disponible:\n{e}", ha="center", va="center", transform=ax.transAxes)

# ── 8. CDF del Error Absoluto ─────────────────────────────────────────────────
ax = axes[7]
for res, color, lbl in [(residuals_new, C1, "MISR Nuevo"), (residuals_paper, C2, "Paper SR")]:
    sae = np.sort(np.abs(res))
    cdf = np.arange(1, len(sae) + 1) / len(sae)
    ax.plot(sae, cdf, color=color, lw=2.2, label=lbl)
    ax.axvline(np.median(np.abs(res)), color=color, ls=":", lw=1.2, alpha=0.7)
ax.set_title("CDF del Error Absoluto", fontweight="bold")
ax.set_xlabel("|Error| (MeV)"); ax.set_ylabel("Fracción Acumulada")
ax.legend(fontsize=9); ax.grid(True, color=CGRD, linewidth=0.5)

# ── 9. Tabla de Estadísticas completa ────────────────────────────────────────
ax = axes[8]
ax.axis("off")
table_data = [
    ["Estadístico",  "MISR Nuevo",                              "Paper SR"],
    ["RMSE (MeV)",   f"{rmse_new:.4f}",                        f"{rmse_paper:.4f}"],
    ["MAE  (MeV)",   f"{mae_new:.4f}",                         f"{mae_paper:.4f}"],
    ["R²",           f"{r2_new:.5f}",                          f"{r2_paper:.5f}"],
    ["Max |Err|",    f"{np.abs(residuals_new).max():.2f}",     f"{np.abs(residuals_paper).max():.2f}"],
    ["Std Error",    f"{np.std(residuals_new):.4f}",           f"{np.std(residuals_paper):.4f}"],
    ["Sesgo (μ)",    f"{residuals_new.mean():.4f}",            f"{residuals_paper.mean():.4f}"],
    ["Mediana |e|",  f"{np.median(np.abs(residuals_new)):.4f}",f"{np.median(np.abs(residuals_paper)):.4f}"],
    ["Núcleos test", str(len(Y_true)),                         str(len(Y_true))],
]
tbl = ax.table(cellText=table_data, loc="center", cellLoc="center", edges="horizontal")
tbl.auto_set_font_size(False); tbl.set_fontsize(10.5); tbl.scale(1.15, 2.1)
for col in range(3):
    tbl[(0, col)].set_facecolor("#1f6feb")
    tbl[(0, col)].set_text_props(color="white", fontweight="bold")
ax.set_title("Resumen Estadístico Completo", fontsize=13, fontweight="bold", pad=28)

plt.tight_layout()
out = "comparison_test_detailed.png"
plt.savefig(out, facecolor=BG, dpi=130, bbox_inches="tight")
print(f"\nDashboard guardado como '{out}'")

