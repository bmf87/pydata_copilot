import json
import glob
import os

def clean_notebook(filepath):
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            notebook = json.load(f)
            
        modified = False
        
        # 1. Clean Global Notebook Metadata
        if 'metadata' in notebook and 'widgets' in notebook['metadata']:
            del notebook['metadata']['widgets']
            modified = True
            
        # 2. Clean Cell Metadata
        if 'cells' in notebook:
            for cell in notebook['cells']:
                if 'metadata' in cell and 'widgets' in cell['metadata']:
                    del cell['metadata']['widgets']
                    modified = True
                    
                # Secondary cleanup: Some outputs contain widget views that also crash GitHub
                if 'outputs' in cell:
                    for output in cell['outputs']:
                        if 'data' in output and 'application/vnd.jupyter.widget-view+json' in output['data']:
                            del output['data']['application/vnd.jupyter.widget-view+json']
                            modified = True

        if modified:
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(notebook, f, indent=1, ensure_ascii=False)
            print(f"Scrubbed widget metadata from {filepath}")
        else:
            print(f"No widget metadata found in {filepath} (Already Clean)")
            
    except Exception as e:
        print(f"Error processing {filepath}: {e}")

if __name__ == "__main__":
    notebook_files = glob.glob('notebooks/*.ipynb')
    for nb in notebook_files:
        clean_notebook(nb)
