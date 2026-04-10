import nbformat as nbf

nb = nbf.v4.new_notebook()

cells = []

cells.append(nbf.v4.new_markdown_cell("""# Evaluación y Comparación de Modelos MISR

En este notebook vamos a cargar los datos de prueba (`X_test`, `y_test`) y a evaluar dos modelos:
1. **Nuestro Modelo Avanzado MISR (CNN + MLP)**: El cual acabamos de entrenar.
2. **Modelo Baseline (Random Forest / Symbolic Regression)**: El modelo base original que sirvió como punto de partida, en este caso nos provee con el baseline contra el que comparamos.

Finalmente, al predecir sobre el conjunto de test para ambos modelos, consolidaremos los resultados en un `comparison_results.csv` para posteriores análisis, gráficas de dispersión y distribución de errores."""))


cells.append(nbf.v4.new_markdown_cell("""## 1. Importación de Librerías y Carga de Datos

Cargaremos las mismas herramientas de preprocesamiento para obtener nuestro *test set*. Luego importaremos las utilidades de evaluación."""))

cells.append(nbf.v4.new_code_cell("""import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from sklearn.metrics import mean_squared_error, mean_absolute_error, r2_score
from tensorflow.keras.models import load_model

import joblib
from data_preprocessing import MISRPreprocessor
from sklearn.model_selection import train_test_split

sns.set_theme(style="whitegrid")"""))

cells.append(nbf.v4.new_markdown_cell("""## 2. Preparar el Conjunto de Pruebas

Recreamos la división de los datos usando la misma semilla (`random_state=42`) para garantizar que estamos validando exactamente sobre el mismo conjunto `test` que se apartó durante el entrenamiento."""))


cells.append(nbf.v4.new_code_cell("""# Usar el procesador con configuraciones idénticas
preprocessor = MISRPreprocessor(grid_size=32)
raw_df = pd.read_csv('dataset_combined.csv')
X_1d, X_2d, y = preprocessor.prepare_data(raw_df)

X_1d_train, X_1d_test, X_2d_train, X_2d_test, y_train, y_test = train_test_split(
    X_1d, X_2d, y, test_size=0.2, random_state=42
)"""))

cells.append(nbf.v4.new_markdown_cell("""## 3. Carga y Evaluación del Modelo Avanzado (Ours)

Cargamos nuestro modelo `.h5` y generamos las predicciones."""))

cells.append(nbf.v4.new_code_cell("""# Carga del modelo
advanced_model = load_model('model_advanced_misr.h5')

# Predicciones
y_pred_advanced = advanced_model.predict([X_1d_test, X_2d_test]).flatten()

# Cálculo de métricas
rmse_adv = np.sqrt(mean_squared_error(y_test, y_pred_advanced))
mae_adv = mean_absolute_error(y_test, y_pred_advanced)
r2_adv = r2_score(y_test, y_pred_advanced)

print("=== Advanced MISR Model (Ours) ===")
print(f"RMSE: {rmse_adv:.4f}")
print(f"MAE:  {mae_adv:.4f}")
print(f"R2:   {r2_adv:.4f}")"""))

cells.append(nbf.v4.new_markdown_cell("""## 4. Obtención de Resultados Baseline

Para el baseline, previamente habíamos entrenado modelos de regresión y random forest. Cargamos un modelo baseline guardado (e.g. `rf_baseline_model.joblib`), o bien en un script externo `nuclearpy_models/models/BE/sr.py` como indica la literatura. Como aquí no dependemos del path exacto del sr.py para ejecutar el pipeline de notebooks, vamos a utilizar las métricas generadas por el baseline script. Simularemos la carga del baseline si ya lo entrenamos con `scikit-learn`."""))


cells.append(nbf.v4.new_code_cell("""import os

# Asumimos que tenemos `baseline_misr_model.joblib` o cargamos las predicciones guardadas
if os.path.exists('baseline_misr_model.joblib'):
    baseline_model = joblib.load('baseline_misr_model.joblib')
    y_pred_baseline = baseline_model.predict(X_1d_test)
else:
    print("El modelo baseline no se encuentra en el directorio raíz. Entrenando un Random Forest Dummy rápido para efectos de comparación...")
    from sklearn.ensemble import RandomForestRegressor
    baseline_model = RandomForestRegressor(n_estimators=50, random_state=42)
    baseline_model.fit(X_1d_train, y_train)
    y_pred_baseline = baseline_model.predict(X_1d_test)

# Métricas Baseline
rmse_base = np.sqrt(mean_squared_error(y_test, y_pred_baseline))
mae_base = mean_absolute_error(y_test, y_pred_baseline)
r2_base = r2_score(y_test, y_pred_baseline)

print("=== Baseline Model ===")
print(f"RMSE: {rmse_base:.4f}")
print(f"MAE:  {mae_base:.4f}")
print(f"R2:   {r2_base:.4f}")"""))

cells.append(nbf.v4.new_markdown_cell("""## 5. Visualización: Gráfica de Dispersión y Errores

Generamos los gráficos (Scatter plot `Real vs Predicción` y `Distribución de Errores`) para ilustrar visualmente las ganancias del modelo propuesto."""))


cells.append(nbf.v4.new_code_cell("""fig, axes = plt.subplots(1, 2, figsize=(15, 6))

# Subplot 1: Real vs Predicción
axes[0].scatter(y_test, y_pred_baseline, alpha=0.5, label='Baseline', color='orange')
axes[0].scatter(y_test, y_pred_advanced, alpha=0.5, label='Advanced (Ours)', color='blue')
axes[0].plot([y_test.min(), y_test.max()], [y_test.min(), y_test.max()], 'r--', lw=2)
axes[0].set_title('Real vs Precict (MISR)')
axes[0].set_xlabel('Valor Real')
axes[0].set_ylabel('Predicción')
axes[0].legend()

# Subplot 2: Distribución de Errores (KDE Plot)
errors_base = y_test - y_pred_baseline
errors_adv = y_test - y_pred_advanced
sns.kdeplot(errors_base, ax=axes[1], label='Baseline', fill=True, color='orange')
sns.kdeplot(errors_adv, ax=axes[1], label='Advanced (Ours)', fill=True, color='blue')
axes[1].set_title('Distribución Residual (Errores)')
axes[1].set_xlabel('Error')
axes[1].set_ylabel('Densidad')
axes[1].legend()

plt.tight_layout()
plt.show()"""))

cells.append(nbf.v4.new_markdown_cell("""## 6. Generar Set de Datos Final de Resultados (`comparison_results.csv`)

Este archivo guardará los resultados detallados de la comparación."""))


cells.append(nbf.v4.new_code_cell("""# Creamos un Dataframe con las variables True y Predicted de cada modelo
results_df = pd.DataFrame({
    'Real_MISR': y_test,
    'Predicted_Baseline': y_pred_baseline,
    'Predicted_Advanced': y_pred_advanced,
    'Error_Baseline': errors_base,
    'Error_Advanced': errors_adv
})

# Guardamos a CSV
csv_filename = 'comparison_results.csv'
results_df.to_csv(csv_filename, index=False)

print(f"Resultados de la comparación exportados exitosamente a '{csv_filename}'.\n")
results_df.head()
"""))

nb.cells = cells
nbf.write(nb, 'evaluate_models.ipynb')
print("Notebook Generado Exitosamente: evaluate_models.ipynb")
