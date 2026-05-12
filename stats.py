import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt

# Load data
df = pd.read_csv('data/subset_events.csv')


# Important vitals
important_items = [220045, 220179, 220180, 220181, 220277]
summary = df[df['itemid'].isin(important_items)].groupby('itemid')['valuenum'].describe()

print("\nStatistical Summary of Important Vitals:\n")
print(summary)

# Create subplot grid (3 rows, 2 columns)
fig, axes = plt.subplots(3, 2, figsize=(14, 10))

# Flatten axes for easy indexing
axes = axes.flatten()

# Loop through each vital
for i, item in enumerate(important_items):
    subset = df[df['itemid'] == item]
    
    sns.histplot(subset['valuenum'], kde=True, ax=axes[i])
    axes[i].set_title(f'Distribution for itemid {item}')
    axes[i].set_xlabel('Value')
    axes[i].set_ylabel('Frequency')

# Remove extra empty subplot (since 5 plots but 6 spaces)
fig.delaxes(axes[-1])

# Adjust layout
plt.tight_layout()

# Show all plots together
plt.show()


# patient_id = 10001725   # replace with actual subject_id

# patient_df = df[df['subject_id'] == patient_id]
# patient_df['charttime'] = pd.to_datetime(patient_df['charttime'])
# patient_df = patient_df.sort_values(by='charttime')
# patient_stats = patient_df.groupby('itemid')['valuenum'].agg([
#     'count',
#     'mean',
#     'std',
#     'min',
#     'max',
#     'median'
# ])

# print(patient_stats)
# import matplotlib.pyplot as plt

# for item in patient_df['itemid'].unique():
#     subset = patient_df[patient_df['itemid'] == item]
    
#     plt.figure()
#     plt.plot(subset['charttime'], subset['valuenum'])
#     plt.title(f'Patient {patient_id} - itemid {item}')
#     plt.xlabel('Time')
#     plt.ylabel('Value')
#     plt.xticks(rotation=45)
#     plt.show()
# for item in patient_df['itemid'].unique():
#     subset = patient_df[patient_df['itemid'] == item]
    
#     subset = subset.set_index('charttime')
    
#     subset['rolling_mean'] = subset['valuenum'].rolling(window=5).mean()
    
#     plt.figure()
#     plt.plot(subset.index, subset['valuenum'], label='Original')
#     plt.plot(subset.index, subset['rolling_mean'], label='Trend', color='red')
#     plt.legend()
#     plt.title(f'Patient {patient_id} Trend - itemid {item}')
#     plt.show()
# for item in patient_df['itemid'].unique():
#     subset = patient_df[patient_df['itemid'] == item].copy()
    
#     subset['diff'] = subset['valuenum'].diff()
    
#     plt.figure()
#     plt.plot(subset['charttime'], subset['diff'])
#     plt.title(f'Change in Values - itemid {item}')
#     plt.show()
# for item in patient_df['itemid'].unique():
#     subset = patient_df[patient_df['itemid'] == item]
    
#     mean = subset['valuenum'].mean()
#     std = subset['valuenum'].std()
    
#     subset['z_score'] = (subset['valuenum'] - mean) / std
    
#     print(f"\nItem {item} Z-score:")
#     print(subset[['charttime', 'valuenum', 'z_score']].head())