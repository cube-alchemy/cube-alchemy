import pandas as pd

def render_simple_kpi(ax, df: pd.DataFrame):
    print('This is a KPI render function. Render the first value of the dataframe in big font.')
    print("DataFrame shape:", df.shape)
    if df.shape[0] > 0:
        value = df.iloc[0,0]
        ax.text(0.5, 0.5, f"{value:,.2f}", horizontalalignment='center', verticalalignment='center', fontsize=48)
        ax.set_title(df.columns[0], fontsize=24)
    else:
        ax.text(0.5, 0.5, "No data", horizontalalignment='center', verticalalignment='center', fontsize=48)
    ax.axis('off')
    return ax