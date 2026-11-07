# Rapport de capitalisation des données R&D

## Inventaire des sources

- Fichiers trouvés : **62**
  - excel_ancien : 25
  - excel_recent : 24
  - word_etude : 12
  - inconnu : 1

## Chargement

- Études chargées : **12**
- Essais chargés : **48**
- Fichiers en double écartés : **1**
- Fichiers non reconnus : **1**

## Anomalies détectées

**6 anomalies**, chacune avec sa source (fichier et cellule).

| Catégorie | Gravité | Détail | Source |
|---|---|---|---|
| Composant inconnu | haute | 'plastifant DINP' absent de la nomenclature | `2023/ETU-2023-01 Influence du taux de plastifiant/ESS-2023-027.xlsx [Formulation!B8]` |
| Valeur hors plage | haute | ESS-2023-026 : viscosite_1h = 4.6 mPa.s (attendu 500-20000) | `2023/ETU-2023-01 Influence du taux de plastifiant/ESS-2023-026.xlsx [Résultats!B4]` |
| Valeur hors plage | haute | ETU-2022-03 : température de gélification 1800.0 °C (attendu 120-250) | `2022/ETU-2022-03 Comparaison de plastifiants/ETU-2022-03_rapport.docx` |
| Valeur manquante | haute | mesure viscosite_24h vide pour ESS-2023-025 | `2023/ETU-2023-01 Influence du taux de plastifiant/ESS-2023-025.xlsx [Résultats!B5]` |
| Essai en double | moyenne | ESS-2021-004 déjà chargé depuis un autre fichier | `2021/ETU-2021-01 Optimisation du stabilisant/ESS-2021-004 - copie.xlsx` |
| Fichier non reconnu | moyenne | Aucun gabarit connu : à traiter manuellement avec la R&D | `2023/notes_diverses.xlsx` |
