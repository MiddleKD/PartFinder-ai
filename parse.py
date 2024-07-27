import os
from typing import List, Dict, Literal, Union, Tuple
from glob import glob
import pandas as pd
from langchain_core.documents import Document

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

def parse_doc_to_df(documents:List[Document], fields:List[Union[str, Tuple[str]]], img_root_dir:str="") -> pd.DataFrame:
    dict_for_df = {}
    for doc in documents:
        for field in fields:
            if isinstance(field, str):
                if field not in dict_for_df: 
                    dict_for_df[field] = []

                record_value = doc["field"]
                if record_value.endswith((".jpg", ".jpeg", ".png")):
                    record_value = os.path.join(img_root_dir, record_value)
                dict_for_df[field].append(record_value)

            elif isinstance(field, tuple):
                if field[-1] not in dict_for_df: 
                    dict_for_df[field[-1]] = []

                record_value = getattr(doc, field[0])[field[-1]]
                if record_value.endswith((".jpg", ".jpeg", ".png")):
                    record_value = os.path.join(img_root_dir, record_value)
                dict_for_df[field[-1]].append(getattr(doc, field[0])[field[-1]])

    return pd.DataFrame(dict_for_df)

if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv()

    data_fn = os.environ.get("DATA_PATH")
    bps_fns = glob(os.path.join(os.environ.get("BLUEPRINT_DIR"), "*"))

    outerjoin_df = make_outerjoin_df(data_fn)
    features_per_bp = get_features_from_df(outerjoin_df)
    
    print(features_per_bp)