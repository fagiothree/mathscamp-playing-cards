import json
import csv
import uuid
import re



# From https://stackoverflow.com/questions/9662346/python-code-to-remove-html-tags-from-a-string
def cleanhtml(raw_html):
    cleanr = re.compile('<.*?>')
    cleantext = re.sub(cleanr, '', raw_html)
    return cleantext


class UuidCollector:
    def __init__(self):
        self.uuids = dict()

    def collect_uuids(self, data):
        if type(data) is not dict:
            return
        for k,v in data.items():
            #if k == "type" and v == "enter_flow":
                # We don't want replace uuids of other flows, so don't recurse
            #    break
            if type(v) is dict:
                    self.collect_uuids(v)
            elif type(v) is list:
                for entry in v:
                    if (type(entry) is dict and "type" in entry and entry["type"] == "enter_flow"):
                        self.uuids[entry["uuid"]] = str(uuid.uuid4()) 
                        break
                    else:
                        self.collect_uuids(entry)
            elif k.find('uuid') != -1:
                # We found a field whose name contains "uuid"
                # We record this uuid and assign a replacement uuid
                if v is not None:
                    self.uuids[v] = str(uuid.uuid4()) # Generate new random UUID to replace it with
        



f_replacements = open("replacements.json", "r")
replacements = json.load(f_replacements)
f_replacements.close()

container_file = open("template_container.json", "r")
container = json.load(container_file)

flow_info_file = open("flows_info.json", "r")
flow_info = json.load(flow_info_file)
flow_info = []

cardcsv = open('cards.csv')
reader = csv.reader(cardcsv)
for row in reader:
    card = row[0]
    
    
    filebase = row[1].lower().replace(" ", "-")

    # Get flow info (if existing)
    corresp_flow_info = list(filter(lambda fl: fl["doc name"] == row[1], flow_info ))
    if len(corresp_flow_info)== 1:
        have_flow_info = True
        corresp_flow_info = corresp_flow_info[0]
    elif len(corresp_flow_info) == 0:
        have_flow_info = False
    else:
        print("error: multiple info for flow " + row[1])
        break

    # Get content specific json file to read from
    filename = "json/" + filebase + ".json"
    file = open(filename, "r")
    data = json.load(file)

    # Get type of content
    ftype = data["metadata"]["type"]
    ftype = ftype.lower().replace(" ", "") # account for different spellings of "funfact"
    ftype_raw = ftype  # the raw type distinguishes between puzzle and counting
    if ftype == "counting":
        # counting uses the same format as puzzle.
        ftype = "puzzle"

    # Get type specific flow template
    flow_fname = "template_" + ftype + ".json"
    if ftype == "puzzle" and "extension_2" not in data:
        flow_fname = "template_puzzle_1extension.json" # puzzles have two extensions by default, but can have one
    flow_template = open(flow_fname, "r").read()
    # Replace title and all UUIDs
    flow_template = flow_template.replace(replacements[ftype]["name"], "Content-" + ftype_raw.title() + "-" + filebase)
    
    uuid_collector = UuidCollector()
    with open(flow_fname, "r") as read_file:
        template_data = json.load(read_file)
        uuid_collector.collect_uuids(template_data)
    
    for k,v in uuid_collector.uuids.items():
        flow_template = flow_template.replace(k, v)

    # After all the text replacements, we read flow_template as JSON.
    new_flow = json.loads(flow_template)
    # if the flow is in the flow info list, replace the flow uuid with the corresponding one,
    # if it is not, add new object to the flow info list with infos about this flow
    if have_flow_info:
        new_flow.update(uuid = corresp_flow_info["uuid"])
    else:
        #new_flow.update(uuid = str(uuid.uuid4()))
        corresp_flow_info = {}
        corresp_flow_info["flow name"] = new_flow["name"]
        corresp_flow_info["doc name"] = row[1]
        corresp_flow_info["uuid"] = new_flow["uuid"]
        corresp_flow_info["card number"] = card
        flow_info.append(corresp_flow_info)

    # Collect text snippets to replace in the flow
    replacement_dict = dict()
    for repl in replacements[ftype]["texts"]:
        sections = repl.split(" - ")
        # Find the data corresponding to the subsection specified in the replacement
        current_section = data
        found = True
        try:
            # Find the subsection of interest
            for s in sections:
                current_section = current_section[s.strip().lower().replace(" ", "_")]
        except KeyError:
            if ftype != "puzzle" and sections[0] != "Extension 2":
                # It's ok for puzzles not to have a second extension
                print("Section " + repl + " not found in " + filebase)
            found = False
        if found:
            # References is a list of refs rather than a string
            if type(current_section) == list:
                current_section = ''.join(current_section)
            # if sections[0] != "Extension 2":
            if len(current_section) == 0:
                print("Warning: blank answer in Section " + repl + " of " + filebase)
                current_section = "missing"
            elif cleanhtml(current_section)[0] == '[':
                print("Warning: template answer in Section " + repl + " of " + filebase)
            # Put content of section into the replacement dict.
            replacement_dict[repl] = current_section

    
    # Check for NRICH references and remove starting node if there aren't any.
    
    if ftype == "puzzle":
        # For puzzles: We determine whether the puzzle is an NRICH puzzle.
        references = ''.join(data["additional_information"]["references"])
        # The references node should be the first node in the flow.
        assert new_flow["nodes"][0]["actions"][0]["text"] == "Additional information - References"
        if references.lower().find("nrich") != -1:
            # This puzzle is an NRICH puzzle. Fill references node with NRICH information.
            # print("NRICH PUZZLE: " + filebase)
            new_flow["nodes"][0]["actions"][0]["text"] = "The following is based on an NRICH puzzle\\n https://nrich.maths.org/"
        else:
            # Not an NRICH puzzle. Remove references node from flow and UI.
            # print("not NRICH PUZZLE: " + filebase)
            uuid_to_remove = new_flow["nodes"][0]["uuid"]
            del new_flow["nodes"][0]
            new_flow["_ui"]["nodes"].pop(uuid_to_remove)

    # # Replace all these text snippets.
    # # We do a lazy text replacement on the unparsed JSON.
    # for k,v in replacement_dict.items():
    #     flow_template = flow_template.replace(k, v)

    # For each flow node, check the text for whether it should be replaced.
    # If so, strip the target text to replace the template from images,
    # and add these images as attachments instead.
    for node in new_flow["nodes"]:
        if "actions" in node:
            if (len(node["actions"])>0 and node["actions"][0]["type"] == "send_msg"):
                action = node["actions"][0]
                template_text = action["text"]
                quick_replies = action["quick_replies"].copy()

                for k,text in replacement_dict.items():
                    if template_text == k:
                        
                        paragraphs = text.split("</p>\n<p>")
                        paragraphs[0] = paragraphs[0].replace("<p>","")
                        paragraphs[-1] = paragraphs[-1].replace("</p>","")
                        if len(paragraphs) == 0:
                            print("error no paragraphs")

                        node["actions"] = [];            
                        for par in paragraphs:
                            

                            images = re.findall(r'<img.*?>', par)
                            attachment_list = []
                            for image in images:
                                image_filename = re.search(r'src=\".*?\"', image).group()[12:-1]
                                attachment_list.append("image:@(fields.image_path & \"{}\")".format(image_filename))
                            
                            if len(images)>0:
                                text_stripped = " "
                            else:
                                # replace latex formulas with corresponding unicode version
                                if par.startswith("<!-- LaTeX Start -->"):
                                    formulas = par.split("<!-- LaTeX End -->")
                                    par = formulas[1].replace("<!--","").replace("-->","")


                                # strip image tags and trailing whitespace
                                # We also strip Markdown formatting and replace linebreaks with \n,
                                # because RapidPro doesn't support Markdown and JSON doesn't allow linebreaks.
                                text_stripped = cleanhtml(par).strip().replace("\n\n", "\n").replace("&gt;", ">").replace("&lt;", "<")
                        

                            node["actions"].append({
                                "attachments": attachment_list.copy(),
                                "text": text_stripped,
                                "type": "send_msg",
                                "quick_replies": [],
                                "uuid": str(uuid.uuid4())
                            })
                node["actions"][-1]["quick_replies"] = quick_replies.copy()

                        
        if "router" in node and "cases" in node["router"]:
            for case in node["router"]["cases"]:
                if "arguments" not in case:
                    continue
                for i,arg in enumerate(case["arguments"]):
                    for k,v in replacement_dict.items():
                        if arg == k:
                            case["arguments"][i] = v



    # Add this flow to the template_container.
    container["flows"].append(new_flow)

    #create trigger for flow
    new_trigger = {
      "trigger_type": "K",
      "keyword": "vmc_" + corresp_flow_info["card number"].lower(),
      "flow": {
        "uuid": corresp_flow_info["uuid"],
        "name": corresp_flow_info["flow name"]
      },
      "groups": [],
      "channel": None
    }

    new_trigger_with_typo = {
      "trigger_type": "K",
      "keyword": "VMC-" + corresp_flow_info["card number"],
      "flow": {
        "uuid": corresp_flow_info["uuid"],
        "name": corresp_flow_info["flow name"]
      },
      "groups": [],
      "channel": None
    }
    # add trigger words
    container["triggers"].append(new_trigger)
    #container["triggers"].append(new_trigger_with_typo)  # NOT VALID TRIGGER!



# Save filled up template container as JSON file
generated_flows = open("./output/generated_flows.json", "w")
json.dump(container, generated_flows, indent=2)   # ensure_ascii=False
generated_flows.close()

# Update flow info file if flows were added
with open('./flows_info.json', 'w') as outfile:
    json.dump(flow_info, outfile,indent=2)
