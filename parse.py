import os, json
from typing import List, Dict, Literal, Union, Tuple
from PIL import Image
from glob import glob
import pandas as pd

def make_outerjoin_df(
    data_path: str
) -> pd.DataFrame:
    
    df = pd.read_excel(data_path, sheet_name=None)
    outerjoin_df = pd.concat([df[cur] for cur in df])
    return outerjoin_df

def get_features_from_df(
    df:pd.DataFrame,
    mode:Literal["unique", "all"] = "unique"
) -> Dict[str, List[dict]]:
    
    features_per_bp = {}

    if mode == "unique":
        bp_names = df["bp"].unique()
        for bp_name in bp_names:
            features = df[df["bp"] == bp_name].iloc[0].drop(["bp"]).dropna().to_dict()
            features_per_bp[bp_name] = [features]
    
    else:  # mode == "all"
        for _, row in df.iterrows():
            bp_name = row["bp"]
            features = row.drop(["bp"]).dropna().to_dict()
            
            if bp_name not in features_per_bp:
                features_per_bp[bp_name] = []
            features_per_bp[bp_name].append(features)
        
    return features_per_bp

def parse_dict_to_df(datas:Dict, fields:List[Union[str, Tuple[str]]]) -> pd.DataFrame:
    dict_for_df = {}
    
    def _get_from_jsonlike(jsonlike:Union[str, dict], key:str):
        if not isinstance(jsonlike, dict):
            jsonlike = json.loads(jsonlike)
        return jsonlike[key]
    
    for field in fields:
        if isinstance(field, str):
            col = []
            
            for record in datas[field]:
                col.append(record)
            dict_for_df[field] = col

        elif isinstance(field, tuple):
            col = []

            for jsonlike in datas[field[0]]:
                for key in field[1:]:
                    jsonlike = _get_from_jsonlike(jsonlike, key)
                record = jsonlike
                col.append(record)
            dict_for_df[field[-1]] = col

    return pd.DataFrame(dict_for_df)

if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv()

    data_fn = os.environ.get("DATA_PATH")
    bps_fns = glob(os.path.join(os.environ.get("BLUEPRINT_DIR"), "*"))

    outerjoin_df = make_outerjoin_df(data_fn)
    features_per_bp = get_features_from_df(outerjoin_df)
    
    print(features_per_bp)