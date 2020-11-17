import json
import csv
import os.path
from os.path import isfile, join
from os import listdir

f_to_translate = open("fields_for_translation.json", "r")
fields_to_translate = json.load(f_to_translate)
f_to_translate.close()


full_set_of_translation = dict()


cardcsv = open('cards.csv')
reader = csv.reader(cardcsv)
for row in reader:
    bits_to_translate = dict()

    # Get content specific json file to read from
    filebase = row[1].lower().replace(" ", "-")
    f_curr_content = open("json/" + filebase + ".json", "r")
    curr_content = json.load(f_curr_content)
    f_curr_content.close()

    
    bits_to_translate[curr_content["title"]] = curr_content["title"]
    if curr_content["title"] not in full_set_of_translation:
        full_set_of_translation[curr_content["title"]] = curr_content["title"]
    
    for k1,v1 in curr_content.items():
        if k1 == "title" or k1 == "metadata":
            continue
        else:
            for k2,v2 in v1.items():
                if fields_to_translate[k1][k2] == "N":
                    continue
                else: 
                    paragraphs = v2.split("</p>\n<p>")
                    paragraphs[0] = paragraphs[0].replace("<p>","")
                    paragraphs[-1] = paragraphs[-1].replace("</p>","")
                    for par in paragraphs:
                        if (par not in bits_to_translate and not(par.startswith("<img")) and not(par.startswith("<!-- LaTeX Start"))):

                            bits_to_translate[par] = par
                            if par not in full_set_of_translation:
                               full_set_of_translation[par] = par

    
    with open('translation/crowdin-files/input/single-files/'+ filebase +'_for_translation.json', 'w') as outfile:
        json.dump(bits_to_translate, outfile,indent=2)



    
with open('translation/crowdin-files/input/full_file_for_translation.json', 'w') as outfile:
    json.dump(full_set_of_translation, outfile,indent=2)


