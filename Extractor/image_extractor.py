import os
import fitz  # PyMuPDF
import re
from PIL import Image
import io
import numpy as np
from multi_coulumn import column_boxes
import matplotlib.pyplot as plt
import pickle


class Box:
    def __init__(self, bbox, data,type):
        self.type = type
        self.bbox = bbox
        self.data = data


def detect_tables(page): ## Detects tables in page
    tables = page.find_tables(horizontal_strategy="lines", vertical_strategy="lines")
    return tables
def find_min(group): ## Finds minimum coordinate value of bounding box group
    if len(group)>0:
        sorted_group = sorted(group,key=lambda x:x.bbox[0])
        return sorted_group[0].bbox[0]
    return 0
    

def normalize_text(text):
    # Remove line breaks and extra spaces
    if(text == None):
        return
    text = text.replace('\n', ' ').strip()
    # Lowercase the text
    text = text.lower()
    # Standardize punctuation
    text = text.replace(' ,', ',').replace(' .', '.').replace(' ?', '?').replace(' !', '!')
    # Replace placeholders (if any)
    # No placeholders to replace in the provided text
    return text


def get_image_list(page,doc):
    images = page.get_image_info(xrefs=True)
    image_list = []
    for image in images:
        try:
            xref = image["xref"]

            # extract the image bytes 
            pix = fitz.Pixmap(doc,xref) 

            # get the image extension 
            if pix.n - pix.alpha > 3: # CMYK: convert to RGB first
                    pix = fitz.Pixmap(fitz.csRGB, pix)
            image_bytes = pix.tobytes()
            img = Image.open(io.BytesIO(image_bytes))
            image_array = np.array(img)
            if(len(np.unique(image_array))!=1):
                box = Box(image['bbox'],np.array(img),"image")
                image_list.append(box)
        except:
            pass
    return image_list
    
    

def get_text_list(page):
    bboxes = column_boxes(page, header_margin=40, no_image_text=True)
    rect_list = []

    for rect in bboxes:
        bbox = rect.rect
        box_string = page.get_text(clip=bbox, sort=True)
        data = normalize_text(box_string)
        box = Box(bbox,data,"text")
        rect_list.append(box)
    return rect_list


def group_coordinates(box_list, threshold,tables):
    groups = []
    current_group = []

    # Sort the coordinates based on the x-coordinate
    sorted_boxes = sorted(box_list, key=lambda x: x.bbox[0])
    # Iterate through sorted coordinates
    for i in range(len(sorted_boxes)):

        if i == 0:
            current_group.append(sorted_boxes[i])
        else:
            # Check the difference between consecutive x-coordinates
            diff = sorted_boxes[i].bbox[0] - sorted_boxes[i-1].bbox[0]
            if diff <= threshold:
                # Add coordinate to the current group
                current_group.append(sorted_boxes[i])
            else:
                # Start a new group
                if tables.tables:
                    for table in tables:
                        min_x = find_min(current_group)
                        if min_x<int(table.bbox[0]):
                            groups.append(current_group)
                else:
                    groups.append(current_group)
                current_group = [sorted_boxes[i]]

    # Add the last group
    if tables.tables:
        for table in tables:
            min_x = find_min(current_group)
            if min_x<int(table.bbox[0]):
                groups.append(current_group)
    else:
        groups.append(current_group)
    return groups

def read_group(group):
    string = ""
    for rect in group:
        if(rect.type=='image'):
            pass
        else:
            string =string + rect.data
    return string

def is_image_group(group):
    for ind,rect in enumerate(group):
        if(rect.type=='image'):
            return ind
    return -1

def doc_extractor(doc_path,doc_name):
    image_dictionary = {}
    doc = fitz.open(doc_path) ## Replace Path with your own PDF Path
    page_count = doc.page_count
    doc_name,ext = doc_name.split('.pdf')
    for i in range(page_count):
        page = doc.load_page(i)
        tables = detect_tables(page)

        bboxes = column_boxes(page, header_margin=40, no_image_text=True) ## Finds all the bounding boxes in the page
        image_list = get_image_list(page,doc) 
        rect_list = get_text_list(page)
        # Function to group coordinates based on their x-coordinate values

        groups = group_coordinates(rect_list+image_list,70,tables)
        for ind,group in enumerate(groups):
                string = ""
                # print(group)
                sorted_group = sorted(group,key=lambda x:x.bbox[1])
                if(is_image_group(sorted_group)!=-1):
                    if((ind-1)>=0):
                        string = string + read_group(sorted(groups[ind-1],key=lambda x:x.bbox[1]))
                    string = string + read_group(sorted(groups[ind],key=lambda x:x.bbox[1]))

                    if((ind+1)<len(groups)):
                        string = string + read_group(sorted(groups[ind+1],key=lambda x:x.bbox[1]))
                # read_group(sorted_group)
                    image_dictionary[group[is_image_group(sorted_group)]] = string

    
    file_path = './Images/doc_name_images.pkl'
    # Save the dictionary to a pickle file
    with open(file_path, 'wb') as pickle_file:
        pickle.dump(image_dictionary, pickle_file)

    print('extracting ',doc_name,' finished')


data_path = './Data/'

for filename in os.listdir(data_path):
    print('extracting ',filename)
    doc_extractor(os.path.join(data_path,filename),filename) 