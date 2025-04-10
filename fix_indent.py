with open('app/pages/patient_view.py', 'r') as f:
    lines = f.readlines()

# Fix indentation on lines 126-128
lines[125] = '            patients_df = db_query.get_all_patients()
'
lines[126] = '            if self.show_active_only:
'
lines[127] = '                patients_df = patients_df[patients_df[\'active\'] == 1]
'

