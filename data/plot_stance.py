import os
import re
import pandas as pd
import matplotlib.pyplot as plt

def plot_stance_over_time(work_dir):
    # Map stance to numeric
    stance_map = {'FAVOR': 1, 'FOR': 1, 'AGAINST': 0}
    files = {
        'Joe Biden': 'Joe Biden_results.csv',
        'Bernie Sanders': 'Bernie Sanders_results.csv',
        'Donald Trump': 'Donald Trump_results.csv'
    }
    plt.figure(figsize=(12, 6))

    for label, fname in files.items():
        path = os.path.join(work_dir, fname)
        df = pd.read_csv(path)
        df['stance_num'] = df['Predicted_Stance'].map(stance_map)

        # Extract timestamp from the diff text using regex (adjust if needed)
        # Example pattern: 2021-06-19T12:34:56Z or similar
        df['timestamp'] = df['Tweet'].str.extract(r'(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z)')
        if df['timestamp'].isnull().all():
            df['timestamp'] = df['Tweet'].str.extract(r'(\d{4}-\d{2}-\d{2})')

        df = df.dropna(subset=['timestamp', 'stance_num'])
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        # Sort by timestamp
        df = df.sort_values('timestamp')
        print(label)
        print(df['stance_num'])
        plt.plot(df['timestamp'], df['stance_num'], label=label, marker='o', linestyle='-')

    plt.xlabel('Timestamp')
    plt.ylabel('Political Stance (1=FOR/FAVOR, 0=AGAINST)')
    plt.title('Predicted Political Stance Over Time')
    plt.legend()
    plt.tight_layout()
    plt.show()

plot_stance_over_time('/Users/vaishnav/Documents/Acad/WSE_proj/WikiStance/data/bert_output/debate')