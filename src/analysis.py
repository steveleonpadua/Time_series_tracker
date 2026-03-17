def clean_timeseries(df):
    
    df['period'] =  pd.to_datetime(df['period'])
    df = df.sort_values("period")

    full_range = pd.date_range(
        start=df["period"].min(),
        end=df["period"].max(),
        freq="D"
    )

    df = df.set_index("period").reindex(full_range)
    
    z = (df["value"] - df["value"].mean()) / df["value"].std()
    df.loc[abs(z) > 4, "value"] = np.nan
    df["value"] = df["value"].interpolate()
    
    return df
