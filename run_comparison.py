import pandas as pd
import numpy as np
import time
from sklearn.metrics import mean_squared_error, mean_absolute_error, r2_score
from misr_advanced import MISR_Model
import sys
import os

sys.path.append(os.path.abspath('nuclearpy_models'))
from models.BE.sr import sr_be

def prepare_features(df):
    df = df.copy()
    df['A'] = df['N'] + df['Z']
    df['I'] = (df['N'] - df['Z']) / df['A']
    z_magic = np.array([2, 8, 20, 28, 50, 82, 126])
    n_magic = np.array([2, 8, 20, 28, 50, 82, 126, 184])
    df['Np'] = np.min(np.abs(df['Z'].values[:, None] - z_magic[None, :]), axis=1)
    df['Nn'] = np.min(np.abs(df['N'].values[:, None] - n_magic[None, :]), axis=1)
    df['P'] = np.where((df['Nn'] + df['Np']) > 0, (df['Nn'] * df['Np']) / (df['Nn'] + df['Np']), 0.0)
    if 'uBE' in df.columns:
        df.rename(columns={'uBE': 'bindingEnergyUncertainty'}, inplace=True)
    return df

def run_comparison():
    print("Loading data...")
    df_train = pd.read_csv("Data/Experimental/be_train.csv")
    df_test = pd.read_csv("Data/Experimental/be_test.csv")

    df_train = prepare_features(df_train)
    df_test = prepare_features(df_test)

    print("Training MISR Model (Fast Settings for preview)...")
    # Reducimos los parámetros para un entrenamiento rápido en demostración
    misr = MISR_Model(maxiter=10, k_folds=5, s_features=4, n_generations=20)
    
    start_time = time.time()
    misr.fit(df_train, target_col='BE')
    misr_train_time = time.time() - start_time
    print(f"MISR Training completed in {misr_train_time:.2f}s")
    
    print("Evaluating models on test set...")
    df_test_filt = df_test[(df_test['Z'] >= 12) & (df_test['Z'] <= 50)].copy()
    df_test_filt = df_test_filt.dropna(subset=['BE']).reset_index(drop=True)
    
    y_true = df_test_filt['BE'].values
    y_pred_misr = misr.predict(df_test_filt)
    
    y_pred_base = []
    for z, n in zip(df_test_filt['Z'], df_test_filt['N']):
        pred, _ = sr_be(z, n)
        y_pred_base.append(pred)
    y_pred_base = np.array(y_pred_base)
    
    def calc_metrics(y_t, y_p):
        rmse = np.sqrt(mean_squared_error(y_t, y_p))
        mae = mean_absolute_error(y_t, y_p)
        r2 = r2_score(y_t, y_p)
        return rmse, mae, r2

    rmse_m, mae_m, r2_m = calc_metrics(y_true, y_pred_misr)
    rmse_b, mae_b, r2_b = calc_metrics(y_true, y_pred_base)
    
    print(f"\n--- COMPARISON RESULTS ---")
    print(f"Number of test samples (Z in [12, 50]): {len(y_true)}")
    print(f"\nMISR Model (Ours):")
    print(f"RMSE: {rmse_m:.4f} MeV")
    print(f"MAE:  {mae_m:.4f} MeV")
    print(f"R^2:  {r2_m:.4f}")
    
    print(f"\nBase SR Model (nuclearpy):")
    print(f"RMSE: {rmse_b:.4f} MeV")
    print(f"MAE:  {mae_b:.4f} MeV")
    print(f"R^2:  {r2_b:.4f}")

    # Generate output table
    df_results = pd.DataFrame({
        'N': df_test_filt['N'],
        'Z': df_test_filt['Z'],
        'A': df_test_filt['A'],
        'True_BE_MeV': y_true,
        'MISR_Pred_MeV': y_pred_misr,
        'MISR_Error': y_true - y_pred_misr,
        'Base_SR_Pred_MeV': y_pred_base,
        'Base_SR_Error': y_true - y_pred_base
    })
    
    csv_path = "comparison_results.csv"
    df_results.to_csv(csv_path, index=False)
    print(f"\nSaved full predictions to {csv_path}")
    
    sample_md = df_results.head(25).to_markdown(index=False, floatfmt=".4f")
    with open("comparison_sample.md", "w") as f:
        f.write("### Muestra de Predicciones: Valores Reales vs Estimados\n")
        f.write("Se presentan los primeros 25 núcleos evaluados de la validación cruzada. El archivo completo de los 1291 núcleos está guardado en `comparison_results.csv`.\n\n")
        f.write(sample_md)

if __name__ == '__main__':
    run_comparison()
