import time
from chain.knowledgebase import KnowledgeBaseTemplateChain
from chain.retriever import DocRetrieverManager
from parse_data import make_outerjoin_df, get_features_from_df

if __name__ == "__main__":
    import os
    from dotenv import load_dotenv

    load_dotenv()

    data_fn = os.environ.get("DATA_PATH")
    bp_dir = os.environ.get("BLUEPRINT_DIR")
    retry_count = int(os.environ.get("RETRY_COUNT"))

    outerjoin_df = make_outerjoin_df(data_fn)
    features_per_bp = get_features_from_df(outerjoin_df, mode="all")
    print("Loaded datas---")

    kb_template_chain = KnowledgeBaseTemplateChain(
        llm_type='google', 
        retry_count=retry_count
    )
    print("Chain loaded---")
    doc_retriever_manager = DocRetrieverManager(
        collection_name="knowledgebase", 
        persist_directory="./chroma"
    )
    print("Retriever loaded---")
    
    bp_kbtemplate_map = {}
    for bp_name, features_list in features_per_bp.items():
        bp_path = os.path.join(bp_dir, bp_name + ".jpg")
        kb_template = kb_template_chain.invoke(bp_path, features_list[0])
        bp_kbtemplate_map[bp_name] = kb_template
        print(f"{bp_name} template gen---")
        time.sleep(5)

    for bp_name, features_list in features_per_bp.items():
        
        for _ in range(retry_count):
            try:
                formed_features_list = doc_retriever_manager.insert_feature_list_into_template(
                        features_list=features_list,
                        template=bp_kbtemplate_map[bp_name],
                        insert_mode="safe",
                        check_template_matched=False
                    )
                print(f"{bp_name} template matched---")
                break
            except ValueError as e:
                kb_template = kb_template_chain.invoke(bp_path, features_list[0])
                bp_kbtemplate_map[bp_name] = kb_template
                print(f"Wrong format {bp_name} template re gen {e}---")

        doc_retriever_manager.insert_dict(formed_features_list, check_is_kb=True)
        print(f"{bp_name} inserted---")