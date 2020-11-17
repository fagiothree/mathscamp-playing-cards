import json
import csv
import os.path
from os.path import isfile, join
from os import listdir

cardcsv = open('cards.csv')
reader = csv.reader(cardcsv)

f_to_translate = open("fields_for_translation.json", "r")
fields_to_translate = json.load(f_to_translate)
f_to_translate.close()


for row in reader:
    
    # Get content specific json file to read from
    filebase = row[1].lower().replace(" ", "-")
    
    f_curr_content = open("json/" + filebase + ".json", "r")
    curr_eng_content = json.load(f_curr_content)
    f_curr_content.close()

    f_transl_content = open("translation/crowdin-files/output/eng/" + filebase + "_for_translation.json", "r")
    curr_translation = json.load(f_transl_content)
    f_transl_content.close()

    curr_eng_content["title"] = curr_translation[curr_eng_content["title"]]

    for k1,v1 in curr_eng_content.items():
        if k1 == "title" or k1 == "metadata":
            continue
        else:
            for k2,v2 in v1.items():
                if fields_to_translate[k1][k2] == "N":
                    continue
                else: 
                    new_v2 = v2
                    
                    paragraphs = v2.split("</p>\n<p>")
                    paragraphs[0] = paragraphs[0].replace("<p>","")
                    paragraphs[-1] = paragraphs[-1].replace("</p>","")
                    for par in paragraphs:
                        if par in curr_translation:
                            new_v2 = new_v2.replace(par, curr_translation[par])
                            
                        elif (not(par.startswith("<img")) and not(par.startswith("<!-- LaTeX Start"))):
                            print("no translation found for " + par)
                    
                    
                    curr_eng_content[k1][k2] = new_v2

    with open('translation/eng/'+ filebase + '.json', 'w') as outfile:
        json.dump(curr_eng_content, outfile,indent=2)