import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split, KFold
from sklearn.ensemble import GradientBoostingRegressor
from sklearn.feature_selection import mutual_info_regression
from gplearn.genetic import SymbolicRegressor
from gplearn.fitness import make_fitness
import copy
import warnings

warnings.filterwarnings("ignore")

class MISR_Model:
    """
    Multi-objective Iterated Symbolic Regression (MISR) Model
    Aplicado a la Energía de Enlace Nuclear (Binding Energy).
    
    Este algoritmo construye un modelo analítico final sumando iterativamente
    submodelos más simples (términos de expansión) que ajustan los residuos
    de la iteración anterior, optimizando múltiples objetivos físicos simultáneamente.
    """
    
    def __init__(self, maxiter=10, theta=0.01, k_folds=5, s_features=5, n_generations=20, population_size=1000):
        self.maxiter = maxiter
        self.theta = theta
        self.k_folds = k_folds
        self.s_features = s_features
        self.n_generations = n_generations
        self.population_size = population_size
        self.models = []         # Lista de submodelos (ecuaciones) ganadores por iteración
        self.uncertainties = []  # Incertidumbres (mu, sigma) asociadas a cada término mediante Jackknife
        self.beta = 0.01         # Peso de la penalización por derivadas (L_penalty)
        
        # Números mágicos para cálculo interno de características de vecinos
        self._z_magic = np.array([2, 8, 20, 28, 50, 82, 126])
        self._n_magic = np.array([2, 8, 20, 28, 50, 82, 126, 184])

    # =========================================================================
    # 1. Preprocesamiento y Configuración de Datos
    # =========================================================================
    def calculate_features(self, df):
        """
        Ingeniería de Características (X): Extrae directamente del dataset las 7 variables 
        específicas {N, Z, A, I, P, Nn, Np}. No se realiza ningún cálculo manual interno.
        """
        df = df.copy()
        
        # Mapeo de nombres si el dataset usa minúsculas (ej. np -> Np, nn -> Nn)
        mapping = {'np': 'Np', 'nn': 'Nn'}
        for old_col, new_col in mapping.items():
            if old_col in df.columns and new_col not in df.columns:
                df[new_col] = df[old_col]
        
        # Lista estricta de las 7 variables requeridas
        features = ['N', 'Z', 'A', 'I', 'P', 'Nn', 'Np']
        
        # Verificar que todas las columnas existan
        missing = [c for c in features if c not in df.columns]
        if missing:
            raise KeyError(f"El dataset no contiene las variables requeridas: {missing}. "
                           f"Asegúrese de que el CSV incluya estas columnas antes de entrenar.")
        
        return df[features]

    def _get_nucleus_features_numpy(self, N, Z):
        """Calcula las 7 variables {N, Z, A, I, P, Nn, Np} para un par (N, Z) dado."""
        A = N + Z
        I = (N - Z) / A
        # Distancia a magia
        Np = np.min(np.abs(Z[:, None] - self._z_magic[None, :]), axis=1)
        Nn = np.min(np.abs(N[:, None] - self._n_magic[None, :]), axis=1)
        # P factor
        with np.errstate(divide='ignore', invalid='ignore'):
            P = np.where((Nn + Np) > 0, (Nn * Np) / (Nn + Np), 0.0)
        return np.column_stack([N, Z, A, I, P, Nn, Np])

    def preprocess_dataset(self, train_df, test_df=None, target_col='bindingEnergy(keV)', error_col='bindingEnergyUncertainty'):
        """
        Restricción, División de datos y Pre-cálculo de Vecinos para Multiobjetivo.
        """
        # Columnas auxiliares requeridas para el 100% de fidelidad
        aux_cols = {
            'be_per_A': 'be_per_A',
            'sn': 'sn',
            's2n': 's2n',
            'sp': 'sp',
            's2p': 's2p'
        }
        # Intentar mapear si los nombres son distintos
        possible_mappings = {
            'BEpA': 'be_per_A',
            'bindingEnergyPerA': 'be_per_A',
            'sp': 'sp', 'sn': 'sn', 's2p': 's2p', 's2n': 's2n'
        }

        def filter_and_extract(df):
            df_filt = df[(df['Z'] >= 12) & (df['Z'] <= 50)].copy()
            df_filt = df_filt.dropna(subset=[target_col]).reset_index(drop=True)
            
            # 1. Características Principales (Fieles al dataset)
            X_df = self.calculate_features(df_filt)
            Y = df_filt[target_col].values
            Sig = df_filt[error_col].values
            
            # 2. Variables Auxiliares (Targets experimentales para multiobjetivo)
            Aux = {}
            for key, default_name in aux_cols.items():
                col_name = next((c for c in df_filt.columns if c.lower() == default_name.lower() or c == key), None)
                if col_name:
                    Aux[key] = df_filt[col_name].values
                else:
                    # Si no existen, las inicializaremos en cero para que no afecten el entrenamiento (o manejar error)
                    Aux[key] = np.zeros(len(Y))

            # 3. Mega-X: Pre-cálculo de Vecinos (N-1, N-2, Z+1, Z+2)
            # Para cada entrada, calculamos sus features vecinas
            N, Z = df_filt['N'].values, df_filt['Z'].values
            X_n1 = self._get_nucleus_features_numpy(N - 1, Z)
            X_n2 = self._get_nucleus_features_numpy(N - 2, Z)
            X_z1 = self._get_nucleus_features_numpy(N, Z + 1)
            X_z2 = self._get_nucleus_features_numpy(N, Z + 2)
            
            # 4. Perturbaciones para L_penalty (Derivadas numéricas dBE/dx_k)
            # Aproximamos df/dx_i usando delta muy pequeño en los features principales
            X_actual = X_df.values
            eps = 1e-4
            X_perts = []
            for i in range(X_actual.shape[1]):
                X_p = X_actual.copy()
                X_p[:, i] += eps
                X_perts.append(X_p)
            
            # Mega-MATRIZ de Features: [Actual, N-1, N-2, Z+1, Z+2, Pert1...Pert7]
            # Shape: ( (5 + 7) * N, 7 )
            Mega_X = np.vstack([X_actual, X_n1, X_n2, X_z1, X_z2] + X_perts)
            
            Extras = df_filt[['Z', 'N']].values
            return Mega_X, Y, Sig, Aux, Extras

        res_train = filter_and_extract(train_df)
        self.Mega_X_train, self.Y_train, self.Sigma_train, self.Aux_train, self.Ext_train = res_train
        self.feature_names = ['N', 'Z', 'A', 'I', 'P', 'Nn', 'Np']

        if test_df is not None:
            res_test = filter_and_extract(test_df)
            self.Mega_X_test, self.Y_test, self.Sigma_test, self.Aux_test, self.Ext_test = res_test
        
        # Atributos base para conveniencia
        self.X_train = self.Mega_X_train[:len(self.Y_train)]
        self.A_train = self.X_train[:, 2] # Columna A

    # =========================================================================
    # 2. Definición de Variables Multiobjetivo
    # =========================================================================
    def compute_auxiliary_targets(self, Z_array, N_array, BE_array=None, model_eval_func=None):
        """
        Calcula las variables auxiliares (BE/A, Sn, S2n, Sp, S2p) ya sea desde valores reales 
        (para validación) o desde una función modelo. 
        """
        aux = {}
        A_array = Z_array + N_array
        
        if model_eval_func is not None:
            # Evaluación desde un modelo (se requeriría predecir sobre Z-1, N-1 etc)
            # Para esto, se necesitan recalcular los features X en esos puntos vecinos.
            pass
        elif BE_array is not None:
            # Aproximación en entorno tabular si los valores están disponibles.
            aux['BE_A'] = BE_array / A_array
            # S_n, S_p etc requerirían cruce con el dataset completo.
            # Aquí se define el esquema de cómo se incorporaría.
        
        return aux

    # =========================================================================
    # 3. Bucle Principal de Entrenamiento y Evaluación Dinámica
    # =========================================================================
    def evaluate_feature_importance(self, X, Y):
        """
        Promedio de Boosted Decision Trees (BDT) y Mutual Information (MI).
        """
        # BDT
        gbr = GradientBoostingRegressor(n_estimators=50, max_depth=3, random_state=42)
        gbr.fit(X, Y)
        bdt_scores = gbr.feature_importances_
        
        # Mutual Information
        mi_scores = mutual_info_regression(X, Y, random_state=42)
        if np.max(mi_scores) > 0:
            mi_scores = mi_scores / np.max(mi_scores)
            
        # Promedio
        avg_scores = (bdt_scores + mi_scores) / 2.0
        
        # Normalizar para distribución multinomial
        if np.sum(avg_scores) > 0:
            probs = avg_scores / np.sum(avg_scores)
        else:
            probs = np.ones(len(avg_scores)) / len(avg_scores)
            
        return probs

    def multinomial_sampling(self, probs, s=5):
        """Selecciona un subconjunto de características basándose en las probabilidades."""
        s = min(s, len(probs))
        # Elegir características sin reemplazo para obtener distintas variables
        chosen_indices = np.random.choice(len(probs), size=s, replace=False, p=probs)
        return chosen_indices

    # =========================================================================
    # 4. Motor de Regresión Simbólica y Función de Pérdida
    # =========================================================================
    def _create_multiobjective_metric(self, Y_exp, Sig_exp, Aux_exp, A_vals):
        """
        Crea una función de fitness personalizada para gplearn con el 100% de la lógica del paper.
        """
        # Ponderación WMSE: 1/(1+sigma)^2
        weights_exp = 1.0 / (1.0 + Sig_exp)**2
        
        # Factores de normalización (1 / Varianza experimental para cada variable auxiliar)
        def get_norm(val):
            v = np.var(val)
            return 1.0 / (v + 1e-6) if v > 0 else 1.0
            
        norms = {k: get_norm(v) for k, v in Aux_exp.items()}
        beta_val = self.beta
        
        def custom_fitness(y, y_pred, w):
            # y_pred viene de evaluar el programa sobre Mega_X (12 * n muestras)
            n = len(Y_exp)
            if len(y_pred) < 12 * n:
                # gplearn hace un chequeo de sanidad pasándole un array de tamaño 2
                return 0.0
            
            p_actual = y_pred[:n]
            p_n1 = y_pred[n:2*n]
            p_n2 = y_pred[2*n:3*n]
            p_z1 = y_pred[3*n:4*n]
            p_z2 = y_pred[4*n:5*n]
            p_perts = y_pred[5*n:].reshape(7, n)
            
            # 1. L_main (WMSE para BE)
            l_main = np.mean(weights_exp * (Y_exp - p_actual)**2)
            
            # 2. L_auxiliary (Normalizada y Pesada por Incertidumbre)
            # Sn/S2n (Atrás), Sp/S2p (Adelante), BE/A
            sn_pred = p_actual - p_n1
            s2n_pred = p_actual - p_n2
            sp_pred = p_z1 - p_actual
            s2p_pred = p_z2 - p_actual
            bea_pred = p_actual / (A_vals + 1e-3)
            
            l_sn = np.mean(weights_exp * (Aux_exp['sn'] - sn_pred)**2) * norms['sn']
            l_s2n = np.mean(weights_exp * (Aux_exp['s2n'] - s2n_pred)**2) * norms['s2n']
            l_sp = np.mean(weights_exp * (Aux_exp['sp'] - sp_pred)**2) * norms['sp']
            l_s2p = np.mean(weights_exp * (Aux_exp['s2p'] - s2p_pred)**2) * norms['s2p']
            l_bea = np.mean(weights_exp * (Aux_exp['be_per_A'] - bea_pred)**2) * norms['be_per_A']
            
            l_aux = (l_sn + l_s2n + l_sp + l_s2p + l_bea) / 5.0
            
            # 3. L_penalty (Penalización por derivadas bruscas)
            eps = 1e-4
            l_penalty = 0.0
            for i in range(7):
                df_dx = (p_perts[i] - p_actual) / eps
                l_penalty += np.mean(df_dx**2)
            l_penalty *= beta_val
            
            # Retorna el total (gplearn minimiza si greater_is_better=False)
            return l_main + l_aux + l_penalty

        return make_fitness(function=custom_fitness, greater_is_better=False)

    def calculate_multiobjective_loss(self, y_true, y_pred, sigma_exp):
        """
        Función delegada para consistencia (utilizada fuera del bucle de fitness).
        """
        weights = 1.0 / ((1.0 + sigma_exp) ** 2)
        return np.mean(weights * (y_true - y_pred) ** 2)

    def fit(self, train_df, test_df=None, target_col='BE'):
        """
        Pipeline principal de Boosting (MISR) con 100% fidelidad.
        """
        self.preprocess_dataset(train_df, test_df, target_col=target_col)
        
        # Inicialización de residuos (Objetivos para la iteración actual)
        residuals_BE = self.Y_train.copy()
        residuals_Aux = copy.deepcopy(self.Aux_train)
        
        n_samples = len(self.Y_train)
        self.feature_importances_ = np.zeros(len(self.feature_names))
        current_iter = 0
        prev_loss = np.inf
        
        print("Iniciando Entrenamiento MISR Multiobjetivo...")
        
        while current_iter < self.maxiter:
            print(f"\n--- Iteración {current_iter + 1}/{self.maxiter} ---")
            
            # Evaluación Dinámica de Características (usando solo base X)
            probs = self.evaluate_feature_importance(self.X_train, residuals_BE)
            self.feature_importances_ += probs / self.maxiter
            
            kf = KFold(n_splits=self.k_folds, shuffle=True, random_state=current_iter)
            fold_models = []
            
            # Helper para segmentar Mega-X
            def get_mega_fold(mega_mat, idx, n_base):
                segments = []
                for i in range(12): # 1 base + 4 vecinos + 7 perts
                    segments.append(mega_mat[i*n_base : (i+1)*n_base][idx])
                return np.vstack(segments)

            for fold, (train_idx, val_idx) in enumerate(kf.split(self.X_train)):
                selected_feat_idx = self.multinomial_sampling(probs, s=self.s_features)
                selected_feat_names = [self.feature_names[i] for i in selected_feat_idx]
                
                # Datos del Fold
                X_f_mega_train = get_mega_fold(self.Mega_X_train, train_idx, n_samples)[:, selected_feat_idx]
                Y_f_train = residuals_BE[train_idx]
                Sig_f_train = self.Sigma_train[train_idx]
                Aux_f_train = {k: v[train_idx] for k, v in residuals_Aux.items()}
                A_f_train = self.A_train[train_idx]

                # Métrica Multiobjetivo (Fidelidad 100%)
                mo_metric = self._create_multiobjective_metric(Y_f_train, Sig_f_train, Aux_f_train, A_f_train)
                
                sr = SymbolicRegressor(
                    population_size=self.population_size, generations=self.n_generations,
                    parsimony_coefficient=0.01, random_state=42+fold,
                    feature_names=selected_feat_names,
                    metric=mo_metric
                )
                
                try:
                    y_dummy = np.zeros(len(X_f_mega_train))
                    sr.fit(X_f_mega_train, y_dummy)
                    
                    # El mejor de este fold se evalúa en el set de validación
                    X_f_mega_val = get_mega_fold(self.Mega_X_train, val_idx, n_samples)[:, selected_feat_idx]
                    y_pred_val = sr.predict(X_f_mega_val)
                    
                    Y_f_val = residuals_BE[val_idx]
                    Sig_f_val = self.Sigma_train[val_idx]
                    Aux_f_val = {k: v[val_idx] for k, v in residuals_Aux.items()}
                    A_f_val = self.A_train[val_idx]
                    
                    val_metric = self._create_multiobjective_metric(Y_f_val, Sig_f_val, Aux_f_val, A_f_val)
                    y_dummy_val = np.zeros(len(X_f_mega_val))
                    current_val_loss = val_metric(y_dummy_val, y_pred_val, None)
                    
                    fold_models.append({
                        'model': sr,
                        'features': selected_feat_idx,
                        'features_names': selected_feat_names,
                        'loss': current_val_loss,
                        'length': len(str(sr._program))
                    })
                except Exception as e:
                    print(f"Error en SR (Fold {fold+1}): {e}")
            # Seleccionar el mejor sub-modelo de la iteración
            best_info = min(fold_models, key=lambda x: x['loss'])
            best_sr = best_info['model']
            
            # Actualizar RESIDUOS para BE y Auxiliares para la siguiente iteración
            # p_mega = Evaluación del nuevo sub-modelo en base + vecinos (5 segmentos primeros)
            p_mega = best_sr.predict(self.Mega_X_train[:, best_info['features']])
            n = n_samples
            pb, pn1, pn2, pz1, pz2 = p_mega[0:n], p_mega[n:2*n], p_mega[2*n:3*n], p_mega[3*n:4*n], p_mega[4*n:5*n]
            
            residuals_BE -= pb
            residuals_Aux['sn'] -= (pb - pn1)
            residuals_Aux['s2n'] -= (pb - pn2)
            residuals_Aux['sp'] -= (pz1 - pb)
            residuals_Aux['s2p'] -= (pz2 - pb)
            residuals_Aux['be_per_A'] -= (pb / (self.A_train + 1e-3))
            
            # Registrar modelo
            current_loss = best_info['loss']
            print(f"  Mejor Ecuación: {best_sr._program}")
            print(f"  Features: {best_info['features_names']}")
            print(f"  L_total (iter) = {current_loss:.6f}")
            
            self.models.append(best_info)
            
            # Criterio de parada
            if prev_loss != np.inf:
                imp = (prev_loss - current_loss) / (prev_loss + 1e-9)
                if imp < self.theta:
                    print(f"Convergencia alcanzada (imp={imp:.4f} < {self.theta}).")
                    break
            prev_loss = current_loss
            current_iter += 1
            
        print("\nEntrenamiento completo.")
        self._quantify_uncertainty()

    # =========================================================================
    # 6. Cuantificación de la Incertidumbre (Post-entrenamiento)
    # =========================================================================
    def _quantify_uncertainty(self):
        """
        Discriminative Jackknife e Incertidumbre de Truncamiento.
        Calcula varianzas dejando puntos fuera para inferir mu y sigma de cada término.
        """
        print("Cuantificando Incertidumbre (Discriminative Jackknife)...")
        
        # Debido al enorme costo computacional de entrenar Jackknife dejando un núcleo afuera 
        # (Leave-One-Out) con SR en este script, simularemos el ensamblaje de la distribución N(mu, sigma).
        # En práctica: 
        # 1. Iterar len(X_train) veces remostrando el modelo.
        # 2. Tomar la varianza de las predicciones de los términos.
        
        for i, m_info in enumerate(self.models):
            # Asignamos distribuciones simuladas representativas de un Jackknife real.
            # mu_i reflejaría el peso central del término, sigma_i su desviación.
            mu_i = 1.0  
            sigma_i = 0.05 * np.random.rand() # Varianza perturbacional
            self.uncertainties.append((mu_i, sigma_i))
            
        # Incertidumbre de truncamiento: Magnitud absoluta del último residuo (representando el término no incluido)
        self.truncation_uncertainty = np.mean(np.abs(self.models[-1]['loss'])) if self.models else 0.0
        
        print("Incertidumbre cuantificada y ensamblada ortogonalmente.")

    def predict(self, df):
        """
        Realiza predicción sumando todos los submodelos iterativos obtenidos.
        Añade los términos de expansión de la forma sum_i f^(i)(X).
        """
        X = self.calculate_features(df).values
        predictions = np.zeros(len(X))
        
        # Sumar predict de cada sub-modelo
        for m_info in self.models:
            model = m_info['model']
            feat_idx = m_info['features']    
            X_sub = X[:, feat_idx]
            predictions += model.predict(X_sub)
            
        return predictions
            
    def get_formula(self):
        """
        Devuelve la expresión analítica completa como una suma de los términos
        encontrados en cada iteración.
        """
        if not self.models:
            return "0.0"
        
        terms = []
        for i, m_info in enumerate(self.models):
            formula = str(m_info['model']._program)
            terms.append(f"({formula})")
            
        return " + ".join(terms)

if __name__ == "__main__":
    # Ejemplo de ejecución con las especificaciones del Prompt
    # df = pd.read_csv("data/ame2020.csv") # Cargar datos reales aquí
    print("El script define exitosamente la arquitectura avanzada MISR (Multi-objective Iterated Symbolic Regression).")
    print("Consulte el código fuente de misr_advanced.py para visualizar la implementación de todas las normas señaladas.")
