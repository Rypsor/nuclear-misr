# Guía Detallada del Proceso de Entrenamiento: Modelo MISR

Este documento describe con exactitud y a nivel técnico cada paso del proceso de entrenamiento del modelo **MISR (Multi-objective Iterated Symbolic Regression)** aplicado a la predicción de Energía de Enlace Nuclear (Binding Energy - BE). El objetivo de esta guía es proporcionar los detalles necesarios en la preparación de datos, la configuración del algoritmo y el flujo del entrenamiento para que el procedimiento sea 100% replicable, basándonos en la implementación provista en `misr_advanced.py` y demostrada en `training_step_by_step.ipynb`.

## 1. Introducción al Algoritmo MISR
MISR es un modelo de *boosting* simbólico iterativo. En lugar de ajustar un solo gran modelo, construye una fórmula de forma aditiva:
$$ \hat{BE}(X) = f^{(1)}(X) + f^{(2)}(X) + \cdots + f^{(K)}(X) $$
Cada término $f^{(k)}(X)$ es una expresión simbólica descubierta mediante programación genética (usando `gplearn`) que busca minimizar el residuo dejado por los términos anteriores. A diferencia del boosting tradicional, optimiza múltiples objetivos físicos de manera simultánea.

---

## 2. Descripción de los Conjuntos de Datos
El procedimiento asume la existencia de datos experimentales divididos en dos conjuntos:
- **Entrenamiento:** `Data/Experimental/be_train.csv` (2749 muestras)
- **Prueba:** `Data/Experimental/be_test.csv` (688 muestras)

### Restricciones Iniciales
Para enfocar el entrenamiento y la evaluación en un rango de validez controlado, se aplican filtros de forma obligatoria previo al entrenamiento duro:
- **Rango de Protones (Z):** Se retienen únicamente los núcleos que satisfacen $12 \leq Z \leq 50$.
- **Tratamiento de nulos:** Se descartan los registros que no posean el valor objetivo de Binding Energy en la columna `BE` o `bindingEnergy(keV)`.

---

## 3. Ingeniería de Características (Feature Engineering)
El modelo opera estrictamente sobre **7 variables físicas**. Estas deben calcularse exactamente en este orden y con esta lógica antes de suministrarse al modelo MISR para entrenamiento o predicción.

A partir del número de neutrones (`N`) y protones (`Z`), se derivan las 5 características adicionales:

1. **`N`**: Número de Neutrones (Base).
2. **`Z`**: Número de Protones (Base).
3. **`A`**: Número Másico. Calculado como $A = N + Z$.
4. **`I`**: Isospín. Calculado como $I = \frac{N - Z}{A}$.
5. **`Np`**: Distancia al número mágico de protones más cercano. Se toma el valor absoluto mínimo con respecto a la serie de capas mágicas `[2, 8, 20, 28, 50, 82, 126]`.
6. **`Nn`**: Distancia al número mágico de neutrones más cercano. Se toma el valor absoluto mínimo con respecto a la serie de capas mágicas `[2, 8, 20, 28, 50, 82, 126, 184]`.
7. **`P`**: Factor de polarización (Valencia n-p empírica). Calculado como:
   $$ P = \frac{N_n \cdot N_p}{N_n + N_p} $$
   *(Si el denominador es cero y se invalida la división temporalmente, se fuerza el término a que valga $P=0$)*.

*Nota:* El dataset contiene la incertidumbre experimental de la variable objetivo, usualmente bajo la columna `uBE`, que el modelo requiere renombrar a `bindingEnergyUncertainty` para su inyección correcta como peso de confiabilidad.

---

## 4. Estructura "Mega-X" (Preparación para Evaluación Multiobjetivo)
Para poder verificar las penalizaciones de suavidad por derivadas y las condiciones de consistencia con núcleos adyacentes sin consultar el dataset experimental dinámicamente o perder optimización, se conforma inicialmente una súper-matriz de características llamada **Mega-X**.
Por cada núcleo de interés se pre-calculan de un golpe las 7 variables para 12 situaciones:
1. El núcleo actual: $(N, Z)$
2. Núcleo vecino $N-1$: $(N-1, Z)$
3. Núcleo vecino $N-2$: $(N-2, Z)$
4. Núcleo vecino $Z+1$: $(N, Z+1)$
5. Núcleo vecino $Z+2$: $(N, Z+2)$
6. Siete (7) perturbaciones: Pequeños desplazamientos espaciales de la forma $(X_i + 10^{-4})$ individualmente a lo largo de cada una de las 7 variables, necesarias luego para construir la derivada numérica aproxima $\frac{\partial f}{\partial x_i}$.

Consecuencia: si se tienen $M$ muestras formales de entrenamiento, la longitud introducida en la regresión evolutiva es de forma latente una matriz de $(12 \times M, 7)$.

---

## 5. Configuración Paramétrica (Hiperparámetros de Regresión)
Se instancia la clase de control principal `MISR_Model` con los siguientes limitantes clave de búsqueda simbólica:
- `maxiter = 10`: El algoritmo iterará creando 10 sub-términos independientes que formarán el modelo aditivo.
- `theta = -1` (u opcionalmente 0.01 si se desea frenado por estancamiento): Es el factor de convergencia de tolerancia temprana, al estar negativo, obligará ininterrumpidamente las 10 corridas por diseño manual.
- `k_folds = 5`: El dataset Mega se divide localmente cada iteración usando validación cruzada en 5 agrupamientos estadísticos; previene la sobre-memorización biológica de combinaciones sintácticas.
- `s_features = 4`: Fuerza al modelo a seleccionar aleatoriamente combinatorias de un subset de 4 variables de las 7 disponibles en pro de diversificar las leyes descubiertas.
- `n_generations = 50`: Es el umbral topológico de gplearn marcando cuántas generaciones biológicas compiten las ecuaciones aleatorias para evolucionar.
- `population_size = 1000`: Volumen del reservorio genético. Expresiones iniciales simultáneas.
- **Reproducibilidad:** Se fija de ser posible una semilla aleatoria (e.g. `random_state=42`) o predefinida en los Folds.

---

## 6. Dinámica del Bucle Principal de Aprendizaje (Iteraciones Boosting)
Por cada iteración $k$ (desde la $1$ hasta la $10$), sucede el siguiente protocolo sistemático:

### 6.1. Selección de Variables (Feature Importance)
Enfrentando las variables $(N, Z, \dots)$ contra el **Residuo Objetivo** dependiente (comenzando como la BE verdadera en iteración 1, luego como $"BE_{real} - predicción\_término_1" \dots$), el sistema extrae las importancias absolutas utilizando dos heurísticas complementarias promediadas:
1. Un bosque `GradientBoostingRegressor`.
2. Escores vía información mutua `mutual_info_regression`.

Por medio de un sorteador multinomial que toma estas probabilidades ponderadas, se determina el subconjunto particular seleccionado (ej. `['A', 'Np', 'N', 'Z']`).

### 6.2. Regresión Simbólica mediante K-Fold
La matriz Mega-X enfocada en ese subset se divide bajo el esquema del `k_folds`. Para cada Fold se inicializa un árbol de `SymbolicRegressor` el cual operará persiguiendo **Minimizar** una función inyectada denominada *Métrica Multiobjetivo*.

### 6.3. La Función de Pérdida Multiobjetivo Personalizada
El motor no busca error estándar sino minimizar un puntaje agregado `greater_is_better=False` definido así, todo ponderado respecto a las incertidumbres locales $1/(1+\sigma_{exp})^2$:
1. **$L_{main}$ (Ajuste BE):** Error cuadrático (WMSE) ponderado sobre la Energía de Enlace experimental en el espacio nominal real.
2. **$L_{aux}$ (Coherencias Físicas Derivadas):** Garantiza exactitudes macroscópicas exigiendo que la fórmula al evaluarse en los puntos vecinos, sus distancias tengan sentido analítico y coincidan contra lo experimentalmente medido para el lote:
   - Separación Neutrones: $S_n \approx f(N, Z) - f(N-1, Z)$
   - Separación 2 Neutrones: $S_{2n} \approx f(N, Z) - f(N-2, Z)$
   - Separación Protones: $S_p \approx f(N, Z+1) - f(N, Z)$
   - Separación 2 Protones: $S_{2p} \approx f(N, Z+2) - f(N, Z)$
   - Fracción por número másico: $BE/A \approx \frac{f(N,Z)}{A}$
3. **$L_{penalty}$ (Suavidad Diferencial):** Extrae las evaluaciones de predicción que correspondían al paquete de 7 puntos perturbados del Mega-X y genera la diferencia marginal respecto a la base $\frac{(Pert_i - Base)}{10^{-4}}$. La sumatoria cuadrática de estas pendientes castigada factorizada por $\beta = 0.01$ impide fórmulas "puntiagudas" altamente sensibles o irregulares.

### 6.4. Escogencia de Fórmula (Frontera de Pareto) y Actualización del Sistema
Acabando los Folds, no se selecciona simplemente la ecuación con menor pérdida, sino que se emplea la **Frontera de Pareto** para equilibrar la precisión y la simplicidad matemática de las expresiones candidatas. El proceso identifica el subconjunto de modelos no dominados (aquellos donde ningún otro modelo tiene menor pérdida y menor longitud simultáneamente) y, dentro de la frontera, se selecciona el punto con la menor distancia a la solución ideal (longitud de descripción y error mínimos).
Dicha fórmula ganadora ingresa a la biblioteca y procede el paso fundamental del Boosting:
El residuo de $BE$ se encoje substrayendo las predicciones exactas reportadas por la nueva ecuación aceptada. Todas las otras variables metas auxiliares ($S_n$, $S_{2p}$) también reducen sus residuos basados en la contribución equivalente evaluada sobre los vecinos.

---

## 7. Cuantificación de la Incertidumbre (Módulo Finalizador)
Al culminar las 10 inserciones aditivas:
El pipeline posee internamente la capacidad formal de implementar *Discriminative Jackknife*, determinando varianzas para cada término hallado frente a datos omitidos, asignando finalmente cuádruplos de precisión ($\mu_i, \sigma_i$). Esto se remata con una incertidumbre de *Truncamiento* dependiente de la magnitud global dejada por los remanentes inabsorbibles, ensamblando intervalos de error fidedignos sin dependencia paramétrica profunda.

---

## 8. Fase de Inferencia (Evaluación sobre Conjunto de Pruebas)
La aplicación del modelo terminado sobre nueva información:
1. El lote `df_test` ingresa al sistema y sus 5 variables sintéticas (`Nn, Np, I, P, A`) se reconstruyen al vuelo desde los $N,Z$ bases sin tocar datos mágicos externos. Se filtra temporalmente reteniendo la ventana $12 \leq Z \leq 50$.
2. Al ordenar un `model.predict()`, las matrices se barren pasando independientemente por los `10` elementos o sub-árboles almacenados y los resultados arrojados se suman lineal y llanamente originando las predicciones combinadas finales $\hat{BE}$.
3. Al cuantificar el diferencial contra la verdad fundamental (`True_BE_MeV`) este procedimiento resulta capaz de mostrar validaciones como los RMSE de ~6.21 MeV (demostrado en notebooks) que marcan la calibración y eficiencia del flujo.

> **Salida Final:** Se consolida una tabla CSV (ej. `comparison_results.csv`) combinando las entradas ($N,Z,A$), la verdad fundamental, y las predicciones y errores computados por el sistema MISR en esta guía y otros referenciales si formaba parte del proceso empírico de comparativa.
