# CELDA 1

import os
import sys
import time
import numpy as np
import pandas as pd
from sklearn.metrics import mean_squared_error, mean_absolute_error, r2_score

# Modelo MISR avanzado
from misr_advanced import MISR_Model

# Modelo base de referencia
sys.path.append(os.path.abspath('nuclearpy_models'))
from models.BE.sr import sr_be

np.random.seed(42)
print("Librerías cargadas correctamente.")


# CELDA 2

df_train = pd.read_csv("Data/Experimental/be_train.csv")
df_test  = pd.read_csv("Data/Experimental/be_test.csv")

print(f"Muestras de entrenamiento : {len(df_train)}")
print(f"Muestras de prueba        : {len(df_test)}")
df_train.head()

#CELDA 3
def prepare_features(df):
    df = df.copy()
    
    # Masa Total e Isospín
    df['A'] = df['N'] + df['Z']
    df['I'] = (df['N'] - df['Z']) / df['A']

    # Distancias a Cierres de Capas (Números Mágicos)
    z_magic = np.array([2, 8, 20, 28, 50, 82, 126])
    n_magic = np.array([2, 8, 20, 28, 50, 82, 126, 184])
    
    df['Np'] = np.min(np.abs(df['Z'].values[:, None] - z_magic[None, :]), axis=1)
    df['Nn'] = np.min(np.abs(df['N'].values[:, None] - n_magic[None, :]), axis=1)

    # Factor P (Interacción protón-neutrón empírica)
    df['P'] = np.where((df['Nn'] + df['Np']) > 0, 
                       (df['Nn'] * df['Np']) / (df['Nn'] + df['Np']), 0.0)

    # El modelo extrae internamente la incertidumbre experimental bajo este nombre clave:
    if 'uBE' in df.columns:
        df.rename(columns={'uBE': 'bindingEnergyUncertainty'}, inplace=True)
        
    return df

df_train = prepare_features(df_train)
df_test  = prepare_features(df_test)

print("✓ Las 7 features maestras han sido calculadas.")

# Comprobamos exclusivamente las variables estrictas que alimentarán el motor:
df_train[['N', 'Z', 'A', 'I', 'P', 'Nn', 'Np']].head(5)


#CELDA 4
misr = MISR_Model(
    maxiter=10,
    theta = -1,
    k_folds=5,
    s_features=4,
    n_generations=50
)

print("Instancia de MISR generada correctamente.")

#CELDA 5
print("Entrenando el modelo MISR...")
start = time.time()

misr.fit(df_train, target_col='BE')

print(f"\nEntrenamiento Finalizado en {time.time() - start:.2f} s")
print(f"El modelo almacenó {len(misr.models)} sub-expresiones de expansión iterativa.")

#CELDA 6
print("\n--- Expresión Analítica del MISR ---")
print(misr.get_formula())

print("\n--- Términos Aprendidos ---")
for i, model_info in enumerate(misr.models):
    print(f"Iteración {i+1}:")
    print(f"  Fórmula: {model_info['model']._program}")
    print(f"  Pérdida (Loss) Valida: {model_info['loss']:.4f}")
    print(f"  Features Activas:      {model_info['features_names']}")

#CELDA 7
df_test_filt = df_test[(df_test['Z'] >= 12) & (df_test['Z'] <= 50)].copy()
df_test_filt = df_test_filt.dropna(subset=['BE']).reset_index(drop=True)

y_true = df_test_filt['BE'].values

y_pred_misr = misr.predict(df_test_filt)

y_pred_base = []
for z, n in zip(df_test_filt['Z'], df_test_filt['N']):
    pred, _ = sr_be(z, n)
    y_pred_base.append(pred)
y_pred_base = np.array(y_pred_base)

rmse_m = np.sqrt(mean_squared_error(y_true, y_pred_misr))
mae_m  = mean_absolute_error(y_true, y_pred_misr)
r2_m   = r2_score(y_true, y_pred_misr)

rmse_b = np.sqrt(mean_squared_error(y_true, y_pred_base))
mae_b  = mean_absolute_error(y_true, y_pred_base)
r2_b   = r2_score(y_true, y_pred_base)

print(f"--- RESULTADOS (Test {len(y_true)} núcleos Z ∈ [12, 50]) ---")
print(f"{'Modelo':<20} | {'RMSE [MeV]':<15} | {'MAE [MeV]':<15} | {'R2':<10}")
print("-"*65)
print(f"{'MISR (Ours)':<20} | {rmse_m:<15.4f} | {mae_m:<15.4f} | {r2_m:<10.4f}")
print(f"{'SR Base (nuclearpy)':<20} | {rmse_b:<15.4f} | {mae_b:<15.4f} | {r2_b:<10.4f}")

#CELDA 8
df_results = pd.DataFrame({
    'N'               : df_test_filt['N'],
    'Z'               : df_test_filt['Z'],
    'A'               : df_test_filt['A'],
    'True_BE_MeV'     : y_true,
    'MISR_Pred_MeV'   : y_pred_misr,
    'MISR_Error'      : y_true - y_pred_misr,
    'Base_SR_Pred_MeV': y_pred_base,
    'Base_SR_Error'   : y_true - y_pred_base
})

csv_path = "comparison_results.csv"
df_results.to_csv(csv_path, index=False)
print(f"Tabla exportada a test-run: {csv_path}")
df_results.head()


