# Past Medical History (PMH) Database Reference

This document provides a comprehensive reference of all PMH data in the mock_patient_data.db database.

## Database Schema

```sql
CREATE TABLE pmh (
    pmh_id INTEGER PRIMARY KEY AUTOINCREMENT,
    patient_id TEXT NOT NULL,
    condition TEXT,
    onset_date TEXT,
    status TEXT,
    notes TEXT,
    code TEXT,
    FOREIGN KEY (patient_id) REFERENCES patients(id) ON DELETE CASCADE
);
```

## Patient PMH Records

### Patient SP001
| pmh_id | patient_id | condition | onset_date | status | notes | code |
|--------|------------|-----------|------------|--------|-------|------|
| 1-6 | SP001 | Type 2 Diabetes | 2023-01-02 | Active | Diagnosed by Dr. Smith | E11 |

### Patient SP002
| pmh_id | patient_id | condition | onset_date | status | notes | code |
|--------|------------|-----------|------------|--------|-------|------|
| 7, 9, 11, 13, 15, 17 | SP002 | Hyperlipidemia | 2022-01-02 | Active | Diagnosed by Dr. Smith | E78.5 |
| 8, 10, 12, 14, 16, 18 | SP002 | Obesity | 2022-01-02 | Active | Diagnosed by Dr. Smith | E66.9 |

### Patient SP003
| pmh_id | patient_id | condition | onset_date | status | notes | code |
|--------|------------|-----------|------------|--------|-------|------|
| 19, 22, 25, 28, 31, 34 | SP003 | Obesity | 2021-01-02 | Resolved | Diagnosed by Dr. Smith | E66.9 |
| 20, 23, 26, 29, 32, 35 | SP003 | Depression | 2021-01-02 | Resolved | Diagnosed by Dr. Smith | F32.9 |
| 21, 24, 27, 30, 33, 36 | SP003 | Anxiety | 2021-01-02 | Resolved | Diagnosed by Dr. Smith | F41.9 |

### Patient SP004
| pmh_id | patient_id | condition | onset_date | status | notes | code |
|--------|------------|-----------|------------|--------|-------|------|
| 37-42 | SP004 | Depression | 2020-01-03 | Active | Diagnosed by Dr. Smith | F32.9 |

### Patient SP005
| pmh_id | patient_id | condition | onset_date | status | notes | code |
|--------|------------|-----------|------------|--------|-------|------|
| 43-48 | SP005 | Anxiety | 2024-01-02 | Active | Diagnosed by Dr. Smith | F41.9 |

### Patient SP006
| pmh_id | patient_id | condition | onset_date | status | notes | code |
|--------|------------|-----------|------------|--------|-------|------|
| 49, 51, 53, 55, 57, 59 | SP006 | Asthma | 2023-01-02 | Resolved | Diagnosed by Dr. Smith | J45.909 |
| 50, 52, 54, 56, 58, 60 | SP006 | COPD | 2023-01-02 | Resolved | Diagnosed by Dr. Smith | J44.9 |

### Patient SP007
| pmh_id | patient_id | condition | onset_date | status | notes | code |
|--------|------------|-----------|------------|--------|-------|------|
| 61, 64, 67, 70, 73, 76 | SP007 | COPD | 2022-01-02 | Active | Diagnosed by Dr. Smith | J44.9 |
| 62, 65, 68, 71, 74, 77 | SP007 | Arthritis | 2022-01-02 | Active | Diagnosed by Dr. Smith | M19.90 |
| 63, 66, 69, 72, 75, 78 | SP007 | Hypothyroidism | 2022-01-02 | Active | Diagnosed by Dr. Smith | E03.9 |

### Patient SP008
| pmh_id | patient_id | condition | onset_date | status | notes | code |
|--------|------------|-----------|------------|--------|-------|------|
| 79-84 | SP008 | Arthritis | 2021-01-02 | Active | Diagnosed by Dr. Smith | M19.90 |

### Patient SP009
| pmh_id | patient_id | condition | onset_date | status | notes | code |
|--------|------------|-----------|------------|--------|-------|------|
| 85-90 | SP009 | Hypothyroidism | 2020-01-03 | Resolved | Diagnosed by Dr. Smith | E03.9 |

### Patient SP010
| pmh_id | patient_id | condition | onset_date | status | notes | code |
|--------|------------|-----------|------------|--------|-------|------|
| 91, 93, 95, 97, 99, 101 | SP010 | Hypertension | 2024-01-02 | Active | Diagnosed by Dr. Smith | I10 |
| 92, 94, 96, 98, 100, 102 | SP010 | Type 2 Diabetes | 2024-01-02 | Active | Diagnosed by Dr. Smith | E11 |

### Patient SP011
| pmh_id | patient_id | condition | onset_date | status | notes | code |
|--------|------------|-----------|------------|--------|-------|------|
| 103, 106, 109, 112, 115, 118 | SP011 | Type 2 Diabetes | 2023-01-02 | Active | Diagnosed by Dr. Smith | E11 |
| 104, 107, 110, 113, 116, 119 | SP011 | Hyperlipidemia | 2023-01-02 | Active | Diagnosed by Dr. Smith | E78.5 |
| 105, 108, 111, 114, 117, 120 | SP011 | Obesity | 2023-01-02 | Active | Diagnosed by Dr. Smith | E66.9 |

### Patient SP012
| pmh_id | patient_id | condition | onset_date | status | notes | code |
|--------|------------|-----------|------------|--------|-------|------|
| 121-126 | SP012 | Hyperlipidemia | 2022-01-02 | Resolved | Diagnosed by Dr. Smith | E78.5 |

### Patient SP013
| pmh_id | patient_id | condition | onset_date | status | notes | code |
|--------|------------|-----------|------------|--------|-------|------|
| 127-132 | SP013 | Obesity | 2021-01-02 | Active | Diagnosed by Dr. Smith | E66.9 |

### Patient SP014
| pmh_id | patient_id | condition | onset_date | status | notes | code |
|--------|------------|-----------|------------|--------|-------|------|
| 133, 135, 137, 139, 141, 143 | SP014 | Depression | 2020-01-03 | Active | Diagnosed by Dr. Smith | F32.9 |
| 134, 136, 138, 140, 142, 144 | SP014 | Anxiety | 2020-01-03 | Active | Diagnosed by Dr. Smith | F41.9 |

### Patient SP015
| pmh_id | patient_id | condition | onset_date | status | notes | code |
|--------|------------|-----------|------------|--------|-------|------|
| 145, 148, 151, 154, 157, 160 | SP015 | Anxiety | 2024-01-02 | Resolved | Diagnosed by Dr. Smith | F41.9 |
| 146, 149, 152, 155, 158, 161 | SP015 | Asthma | 2024-01-02 | Resolved | Diagnosed by Dr. Smith | J45.909 |
| 147, 150, 153, 156, 159, 162 | SP015 | COPD | 2024-01-02 | Resolved | Diagnosed by Dr. Smith | J44.9 |

### Patient SP016
| pmh_id | patient_id | condition | onset_date | status | notes | code |
|--------|------------|-----------|------------|--------|-------|------|
| 163-168 | SP016 | Asthma | 2023-01-02 | Active | Diagnosed by Dr. Smith | J45.909 |

### Patient SP017
| pmh_id | patient_id | condition | onset_date | status | notes | code |
|--------|------------|-----------|------------|--------|-------|------|
| 169-174 | SP017 | COPD | 2022-01-02 | Active | Diagnosed by Dr. Smith | J44.9 |

### Patient SP018
| pmh_id | patient_id | condition | onset_date | status | notes | code |
|--------|------------|-----------|------------|--------|-------|------|
| 175, 177, 179, 181, 183, 185 | SP018 | Arthritis | 2021-01-02 | Resolved | Diagnosed by Dr. Smith | M19.90 |
| 176, 178, 180, 182, 184, 186 | SP018 | Hypothyroidism | 2021-01-02 | Resolved | Diagnosed by Dr. Smith | E03.9 |

### Patient SP019
| pmh_id | patient_id | condition | onset_date | status | notes | code |
|--------|------------|-----------|------------|--------|-------|------|
| 187, 190, 193, 196, 199, 202 | SP019 | Hypothyroidism | 2020-01-03 | Active | Diagnosed by Dr. Smith | E03.9 |
| 188, 191, 194, 197, 200, 203 | SP019 | Hypertension | 2020-01-03 | Active | Diagnosed by Dr. Smith | I10 |
| 189, 192, 195, 198, 201, 204 | SP019 | Type 2 Diabetes | 2020-01-03 | Active | Diagnosed by Dr. Smith | E11 |

### Patient SP020
| pmh_id | patient_id | condition | onset_date | status | notes | code |
|--------|------------|-----------|------------|--------|-------|------|
| 205-210 | SP020 | Hypertension | 2024-01-02 | Active | Diagnosed by Dr. Smith | I10 |

## Summary of Conditions

| Condition | Count | Active | Resolved | ICD-10 Code |
|-----------|-------|--------|----------|------------|
| Type 2 Diabetes | 24 | 24 | 0 | E11 |
| Hyperlipidemia | 18 | 12 | 6 | E78.5 |
| Obesity | 18 | 12 | 6 | E66.9 |
| Anxiety | 18 | 12 | 6 | F41.9 |
| Depression | 18 | 12 | 6 | F32.9 |
| Asthma | 12 | 6 | 6 | J45.909 |
| COPD | 18 | 12 | 6 | J44.9 |
| Arthritis | 18 | 12 | 6 | M19.90 |
| Hypothyroidism | 18 | 12 | 6 | E03.9 |
| Hypertension | 18 | 18 | 0 | I10 | 