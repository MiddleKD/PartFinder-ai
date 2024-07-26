import time
from chain.knowledgebase import KnowledgeBaseTemplateChain
from chain.retriever import DocRetrieverManager
from parse import make_outerjoin_df, get_features_from_df

if __name__ == "__main__":
    import os
    from dotenv import load_dotenv

    load_dotenv()

    data_fn = os.environ.get("DATA_PATH")
    bp_dir = os.environ.get("BLUEPRINT_DIR")
    retry_count = int(os.environ.get("RETRY_COUNT"))

    print("Load datas---")
    outerjoin_df = make_outerjoin_df(data_fn)
    features_per_bp = get_features_from_df(outerjoin_df, mode="all")

    print("Load model chain---")
    kb_template_chain = KnowledgeBaseTemplateChain(
        llm_type='google', 
        retry_count=retry_count
    )

    print("Load retriever---")
    doc_retriever_manager = DocRetrieverManager(
        collection_name="knowledgebase", 
        persist_directory="./chroma"
    )
    
    bp_kbtemplate_map = {}
    for bp_name, features_list in features_per_bp.items():
        bp_path = os.path.join(bp_dir, bp_name + ".jpg")
        kb_template = kb_template_chain.invoke(bp_path, features_list[0])
        bp_kbtemplate_map[bp_name] = kb_template
        print(f"Template for {bp_name} generated---")
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
                print(f"Make docs for {bp_name} template---")
                break
            except ValueError as e:
                kb_template = kb_template_chain.invoke(bp_path, features_list[0])
                bp_kbtemplate_map[bp_name] = kb_template
                print(f"Wrong format {bp_name} template regenerate {e}---")

        print(f"Insert {bp_name} to DB---")
        doc_retriever_manager.insert_dict(formed_features_list, check_is_kb=True)

    print("All process is done.")
