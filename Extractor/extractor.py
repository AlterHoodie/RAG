import os
import fitz  # PyMuPDF
import re
from multi_coulumn import column_boxes

def detect_tables(page): ## Detects tables in page
    tables = page.find_tables(horizontal_strategy="lines", vertical_strategy="lines")
    return tables
def find_min(group): ## Finds minimum coordinate value of bounding box group
    sorted_group = sorted(group,key=lambda x:x[0])
    return sorted_group[0][0]

def normalize_text(text):
    # Remove line breaks and extra spaces
    if text==None:
        return ""
    text = text.replace('\n', ' ').strip()
    # Lowercase the text
    text = text.lower()
    # Standardize punctuation
    text = text.replace(' ,', ',').replace(' .', '.').replace(' ?', '?').replace(' !', '!')
    # Replace placeholders (if any)
    # No placeholders to replace in the provided text
    return text

def group_coordinates(coordinates, threshold,tables):
    groups = []
    current_group = []

    # Sort the coordinates based on the x-coordinate
    sorted_coordinates = sorted(coordinates, key=lambda x: x[0])

    # Iterate through sorted coordinates
    for i in range(len(sorted_coordinates)):
        if i == 0:
            current_group.append(sorted_coordinates[i])
        else:
            # Check the difference between consecutive x-coordinates
            diff = sorted_coordinates[i][0] - sorted_coordinates[i-1][0]
            if diff <= threshold:
                # Add coordinate to the current group
                current_group.append(sorted_coordinates[i])
            else:
                # Start a new group
                if tables.tables:
                    for table in tables:
                        min_x = find_min(current_group)
                        if min_x<int(table.bbox[0]):
                            groups.append(current_group)
                else:
                    groups.append(current_group)
                current_group = [sorted_coordinates[i]]

    # Add the last group
    if tables.tables:
        for table in tables:
            min_x = find_min(current_group)
            if min_x<int(table.bbox[0]):
                groups.append(current_group)
    else:
        groups.append(current_group)
    return groups

## Extracting entire PDF
def page_extractor(page):
    normalized_string = ""
    normalized_table = ""

    tables = detect_tables(page)

    bboxes = column_boxes(page, header_margin=40, no_image_text=True) ## Finds all the bounding boxes in the page

    rect_list = [] 
    for rect in bboxes:## Rect stores the coordinates of the bounding box
        rect_list.append(rect.rect)
    # Function to group coordinates based on their x-coordinate values

    groups = group_coordinates(rect_list,70,tables)

    for group in groups:
        sorted_group = sorted(group,key=lambda x:x[1])
        for rect in sorted_group:
            # print(page.get_text(clip=rect, sort=True))
            # print("-" * 80)
            box_string = page.get_text(clip=rect, sort=True)
            normalized_string = normalized_string + normalize_text(box_string)
    
    for table in tables:
        df = table.to_pandas()
        df_normalized = df.applymap(normalize_text)
        df_normalized.columns = [normalize_text(col) for col in df.columns]
        normalized_table = normalized_table + "\n" + df_normalized.to_csv(index=False)
    return normalized_string + '\n' + normalized_table

def doc_extractor(doc_path,doc_name):
    doc = fitz.open(doc_path) ## Replace Path with your own PDF Path
    page_count = doc.page_count
    doc_name,ext = doc_name.split('.pdf')

    with open(f"./Output/{doc_name}.txt", "a",encoding='utf-8') as file:
        # Iterate through each page
        for i in range(page_count):
            try:
                page = doc.load_page(i)
                # Extract page_string for the current page
                page_string = page_extractor(page)

                # Append page_string to the text file
                file.write(page_string + "\n")
            except:
                pass
    print('extracting ',doc_name,' finished')

data_path = './Data/'

for filename in os.listdir(data_path):
    print('extracting ',filename)
    doc_extractor(os.path.join(data_path,filename),filename) 