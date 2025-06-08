# Shift Scheduling Optimization – Mathematical Formulation (Essential v1.0)

## 1. Sets and Indexing
| Symbol | Description | Typical Size |
|--------|-------------|--------------|
| \(S\) | Set of staff members (index _s_) | ~30 |
| \(T\) | Set of fixed 4‑hour time slots in one planning week (index _t_) | 28 (4 slots × 7 days) |
| \(D\) | Set of days in the planning horizon (index _d_) | 7 |

We map each slot _t_ to a day \(d(t)\).

---


## 2. Parameters (Input Data)

| Symbol                   | Type         | Description                                                      |
| ------------------------ | ------------ | ---------------------------------------------------------------- |
| $\text{Required}_t$      | $\mathbb{N}$ | Minimum number of staff required in slot $t$                     |
| $\text{Avail}_{s,t}$     | $\{0,1,2\}$  | Availability of staff $s$ for slot $t$: 0 = NG, 1 = OK, 2 = Wish |
| $\text{Age}_s$           | $\mathbb{N}$ | Age of staff $s$                                                 |
| $w_s$                    | ¥            | Hourly wage of staff $s$                                         |
| $\alpha_\text{night}$    | $\mathbb{R}$ | Night‐time wage multiplier (e.g., 1.25)                          |
| $\alpha_\text{holiday}$  | $\mathbb{R}$ | Holiday wage multiplier (optional)                               |
| $h_{\min,s}, h_{\max,s}$ | $\mathbb{N}$ | Min / Max contract hours per week for staff $s$                  |
| SlotHours                | 4            | Fixed duration (hours) of each slot                              |
| $\text{NightSlot}_t$     | $\{0,1\}$    | 1 if slot $t$ is between 22–26                                   |
| $\text{Holiday}_d$       | $\{0,1\}$    | 1 if day $d$ is a holiday                                        |


**Weight coefficients** (user-tunable, default 1):

- \(W_1\): labour-cost weight  
- \(W_2\): demand fulfilment weight  
- \(W_3\): wish fulfilment weight  
- \(W_4\): fairness (variance) weight  

These weights linearise a multi-objective trade-off.

---

## 3. Decision Variables

| Variable | Domain | Meaning |
|----------|--------|---------|
| \(x_{s,t}\) | \(\{0,1\}\) | 1 if staff \(s\) is assigned to slot \(t\), else 0 |
| \(h_s\) | \(\mathbb{N}\) (derived) | Total assigned hours for staff \(s\) in the week |

---

## 4. Objective Function

Minimise the weighted sum

$$
\min Z =  
\underbrace{W_1 \sum_{s \in S} \sum_{t \in T} c_{s,t} \, x_{s,t}}_{\text{(a) labour cost}}  
- W_2 \sum_{t \in T} \min\left(\sum_{s \in S} x_{s,t}, \text{Required}_t\right)  
- W_3 \sum_{s \in S} \sum_{t \in T} \delta(\text{Avail}_{s,t}=2) \, x_{s,t}  
+ W_4 \sum_{s \in S} \left(h_s - \overline{h}\right)^2
$$

where  

\[
c_{s,t} = w_s \times \text{SlotHours} \times \left(1 + (\alpha_\text{night} - 1) \, \text{NightSlot}_t + (\alpha_\text{holiday} - 1) \, \text{Holiday}_{d(t)} \right)
\]

\[
\delta(\cdot) \text{ is the Kronecker delta}
\]

\[
\overline{h} = \frac{1}{|S|} \sum_{s} h_s
\]

---

## 5. Constraints

| ID     | Constraint               | Mathematical Formulation                                                                                                            |
| ------ | ------------------------ | ----------------------------------------------------------------------------------------------------------------------------------- |
| **C1** | Demand fulfilment        | $\displaystyle \sum_{s} x_{s,t} \ge \text{Required}_t \quad \forall t \in T$                                                        |
| **C2** | Availability respect     | $\displaystyle x_{s,t} \le \delta(\text{Avail}_{s,t} \ge 1) \quad \forall s,t$                                                      |
| **C3** | Weekly hours upper bound | $\displaystyle h_s = \text{SlotHours} \sum_{t} x_{s,t} \le h_{\max,s} \quad \forall s$                                              |
| **C4** | Weekly hours lower bound | $\displaystyle h_s \ge h_{\min,s} \quad \forall s$                                                                                  |
| **C5** | Daily max 8 h            | $\displaystyle \text{SlotHours} \sum_{t \in T_d} x_{s,t} \le 8 \quad \forall s, d$                                                  |
| **C6** | Rest break (>6 h)        | Sliding‑window: $\displaystyle \sum_{t'=t}^{t+2} x_{s,t'} \le 2 \quad \forall s, \forall t \text{ with } d(t')=d(t)$                |
| **C7** | Weekly 1 day off         | $\displaystyle \sum_{d \in D} \mathbf{1}\Big(\sum_{t\in T_d} x_{s,t} > 0\Big) \le 6 \quad \forall s$ (modelled via helper binaries) |
| **C8** | Under‑18 night ban       | If $\text{Age}_s < 18$: $\displaystyle x_{s,t} = 0 \quad \forall t \text{ with } \text{NightSlot}_t=1$                              |




_All constraints are linear or can be linearised; the model is a 0-1 MILP/CP-SAT of modest size (≈ 840 binaries)._

---

## 6. Implementation Hints (OR-Tools CP-SAT)

- Encode \(h_s\) with an `AddAllowedAssignments` or linear expression.  
- For C6 (rest) use **fixed-window** cardinality constraints.  
- For C7 (day-off) introduce auxiliary binary \(y_{s,d}\) “worked on day”.  
- Objective is linear except the fairness term; linearise by introducing squared-error approximations or use CP-SAT’s `AddQuadraticObjective`.

---

## 7. Excel I/O Mapping

| Excel Sheet | Model Symbol Mapping |
|-------------|---------------------|
| **Staff**   | \(S, \text{Age}_s, w_s, h_{\min,s}, h_{\max,s}\) |
| **Availability** | \(\text{Avail}_{s,t}\) |
| **Demand**  | \(\text{Required}_t\) |
| (output) **Schedule** | decision matrix \(x_{s,t}\) |

---

*Document generated 2025-05-20 (JST).*
