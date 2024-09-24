"""
Program to generate a github wiki sidebar given the wiki markdown files.

Major difference from the github generated sidebar is the ability to
group and order the links using a JSON definition file.

More info at https://github.com/jeffjl74/github-sidebar
"""
import argparse
import json
import os
import re

class SummaryInfo:
    """ Info for a collapsable sidebar heading link, and its subheadings links """
    def __init__(self, name):
        self.summary_name = name
        self.default_group_name = 'Ungrouped'  # so we only need to spell this out in this one place
        self.group_name = self.default_group_name
        self.subheads = []

class SummaryMap:
    def __init__(self, file_name):
        """
        Reads all of the key/value entries in the passed JSON file
        into a self dictionary.

        Instantiation should be wrapped in a try/except to catch decode errors.

        Args:
            file_name (string): The JSON file name.
        """
        with open(file_name, 'r', encoding='utf-8') as deffile:
            self.defs = json.load(deffile)

    def get_group_for_summary(self, summary_name):
        """ Return the group for the given summary_name, or None if not found """
        for key,val in self.defs.items():
            for secname in val:
                if secname == summary_name:
                    return key
        return None
    
    def get_summarys_for_group(self, group_name):
        """ Return the summary details for the given group_name, or None if not found """
        self.summarys = self.defs.get(group_name, None)
        return self.summarys

def urljoin(*args):
    """ join a list of arguments into a URL, fixing extra or missing / delimeters """
    trailing_slash = '/' if args[-1].endswith('/') else ''
    return "/".join([str(x).strip("/") for x in args]) + trailing_slash

def first(iterable, default=None):
  """ find the first matching item """
  for item in iterable:
    return item
  return default

def get_markdown_files(directory):
    """Get a list of markdown files in the given directory."""
    markdown_files = []
    for root, dirs, files in os.walk(directory):
        for file in files:
            if file.endswith('.md'):
                markdown_files.append(os.path.join(root, file))
    return markdown_files

def extract_headings(file_path):
    """
    Extract the main heading and subheadings from a markdown file.
    H1 heading will be the collapsable entry in the sidebar.
    H2 and up headings are shown when H1 is expanded.
    """
    with open(file_path, 'r', encoding='utf-8') as file:
        main_heading = None
        subheadings = []
        for line in file:
            line = line.strip()
            # how many (if any) #'s start the line?
            m = re.search("^#+", line)
            if m:
                # indent level is "how many #'s"
                indent = len(m.group())
                if indent == 1:
                    # H1 = main collapsable link
                    main_heading = line[indent+1:]
                elif indent > 1:
                    # H2 & up = collapsed under H1
                    # indent depth processed later
                    offset = indent + 1 # to skip over the #'s and get the text
                    subheadings.append((indent, line[offset:]))

        # Default to filename if no main heading was found
        if not main_heading:
            main_heading = os.path.basename(file_path.replace('.md', ''))
        
        return main_heading, subheadings

def create_anchor(text):
    """Create an anchor link for a heading text."""
    # Convert text to lowercase, replace spaces with hyphens, remove invalid URL characters
    anchor = re.sub(r'[^\w\s-]', '', text).strip().lower().replace(' ', '-')
    return anchor

def process_args():
    """
    Parses command line and verifies inputs
    """
    parser = argparse.ArgumentParser(description='Generate a Github Wiki sidebar from markdown files. Version 1.0.0',
             epilog='More info here: https://github.com/jeffjl74/github-sidebar')
    parser.add_argument('-s', dest ='summaryDef', 
                    action ='store', help ='Optional JSON summary definition file')
    parser.add_argument('-o', dest ='outputFile', default='_Sidebar.md',
                    action ='store', help ='Sidebar markdown result file. Defaults to "_Sidebar.md" in the current directory.')
    parser.add_argument(dest ='markdownFolder', 
                    action ='store', help ='Path to the folder of markdown files')
    parser.add_argument(dest ='reposName', 
                    action ='store', help ='Path to the github repository in the form user_name/repos_name')
    args = parser.parse_args()

    global directory_path
    directory_path = args.markdownFolder
    if not os.path.isdir(directory_path):
        parser.error('error: could not find input file directory: ' + directory_path)

    global output_file
    output_file = args.outputFile.strip()
    try:
        f = open(output_file, 'w', encoding='utf-8')
        f.close()
    except:
        parser.error(f'could not open output file {output_file}')

    # the base href= path on github to linked pages
    #  (Could not find a relative path that worked in both preview and live on github wiki,
    #   so just build the absolute path. This has the added benefit of testing using the local file.)
    global base_url
    base_url = urljoin('https://github.com/', args.reposName, '/wiki/')

    global summary_map
    if args.summaryDef is not None:
        fname = args.summaryDef.strip()
        if not os.path.isfile(fname):
            print('error: Could not find json file ', fname, '. Files will not be grouped.')
        else:
            try:
                summary_map = SummaryMap(fname)
            except json.JSONDecodeError as de:
                print("Invalid JSON syntax: ", de)

def generate_sidebar():
    """Generate a sidebar markdown file with collapsible subheadings linking to their anchors."""
    
    global directory_path
    global output_file

    markdown_files = get_markdown_files(directory_path)
    summary_list = []

    for md_file in sorted(markdown_files):

        if "sidebar.md" in md_file.lower():
            continue

        main_heading, subheadings = extract_headings(md_file)
        relative_path = os.path.relpath(md_file, directory_path)  # Generate relative path for links

        # gather each summmary separately, for later rearrangement
        summary = SummaryInfo(main_heading)

        # Main heading with link
        relative_url = relative_path.replace('.md', '')
        base_href = f'{base_url}{relative_url}'
        summary.subheads.append(f'<details><summary><a href="{base_href}">{main_heading}</a></summary>')

        if not subheadings:
            # end details
            summary.subheads.append(f'</details>')
            summary.subheads.append(f'\n')

        if subheadings:
            # Add collapsible subheadings with links under the main heading
            summary.subheads.append(f'  <ul>')
            prior_indent = 2 # start at H2
            spaces = '  '  * prior_indent  # for readability of the .md - has no effect on the rendered sidebar
            for indent_level, subheading_anchor in subheadings:
                anchor = create_anchor(subheading_anchor.strip())
                # If the subheading is indented (H3 and up), adjust the indent in the .md
                if  indent_level > prior_indent:
                    spaces = '  ' * indent_level
                    summary.subheads.append(f'{spaces}<ul>')
                    prior_indent = indent_level
                    spaces = '  ' * (indent_level + 1)
                elif indent_level < prior_indent:
                    for count in range(prior_indent, indent_level, -1):
                        spaces = '  ' * count
                        summary.subheads.append(f'{spaces}</ul>')
                    prior_indent = indent_level
                    spaces = '  ' * indent_level

                link = f'{base_href}#{anchor}'
                summary.subheads.append(f'{spaces}<li><a href="{link}">{subheading_anchor.strip()}</a></li>')

            for count in range(indent_level, 1, -1):
                spaces = '  ' * (count - 1)
                summary.subheads.append(f'{spaces}</ul>')
            summary.subheads.append(f'</details>')
            summary.subheads.append(f'\n')
            
        summary_list.append(summary)

    # if we have a summary map, arrange summarys into their group
    if summary_map is not None:
        with open(output_file, 'w', encoding='utf-8') as sidebar:

            # add the group name to the summarys
            for s in summary_list:
                group_name = summary_map.get_group_for_summary(s.summary_name)
                if group_name is not None:
                    s.group_name = group_name

            # write the data in the json order
            for group in summary_map.defs:
                summarys = summary_map.get_summarys_for_group(group)
                if summarys is None:
                    continue
                sidebar.write(f'## {group}\n')
                for index, item in enumerate(summarys):
                    sec = first(x for x in summary_list if x.summary_name == item)
                    if sec is not None:
                        sidebar.write('\n'.join(sec.subheads))

            # add a group for the summarys that didn't get a group name
            ungrouped_header_done = False
            for s in summary_list:
                if s.group_name == s.default_group_name:
                    if not ungrouped_header_done:
                        sidebar.write(f'## {s.group_name}\n')
                        ungrouped_header_done = True
                    sidebar.write('\n'.join(s.subheads))

    else: # no summary map
        # just write the data to the output file in sorted input file order
        with open(output_file, 'w', encoding='utf-8') as sidebar:
            for s in summary_list:
                sidebar.write('\n'.join(s.subheads))
    
    print(f"Sidebar generated: {output_file}")


# command line arguments, set by process_args()
directory_path = '' # path for the input markdown files
base_url = ''       # url for the github project wiki
output_file = ''    # the output file name
summary_map = None  # the optional summary-to-group map from the JSON file

process_args()
generate_sidebar()
