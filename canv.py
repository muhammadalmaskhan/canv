import xmltodict
import networkx as nx
import argparse
from webweb import Web
import webweb


def load_bib(path):
    with open(path) as f:
        data = f.read()
        co_author_lst = []

        def traverse(ipt):
            author_lst = []
            try:
                s_idx = ipt.index('author={')
            except ValueError:
                return
            e_idx = ipt.index('},', s_idx)
            authors = ipt[s_idx + 8:e_idx].split(' and ')
            for author in authors:
                last_name, first_name = author.split(', ')
                author_lst.append(first_name + ' ' + last_name)
            co_author_lst.append(author_lst)
            traverse(ipt[e_idx:])

        traverse(data)
        return co_author_lst


def load_dblp_xml(path):
    with open(path) as f:
        data = xmltodict.parse(f.read())

    co_author_lst = []

    for paper in data['dblpperson']['r']:
        author_lst = []
        paper_type = list(paper.keys())
        if paper_type[0] in ['article', 'inproceedings']:
            authors = paper[list(paper.keys())[0]]['author']
        else:
            continue

        if len(authors) > 2:
            for author in authors:
                try:
                    name = author['#text']
                except TypeError:
                    continue
                if name[-4:].isnumeric():
                    name = name[:-5]
                if '(-)' in name:
                    name = name.replace('(-)', '')
                author_lst.append(name)
        else:
            continue
        co_author_lst.append(author_lst)

    return co_author_lst


def build_graph(co_author_lst, min_weight, frequent_co_authors=None, show_percentage_names=0):
    g = nx.Graph()

    for paper_author in co_author_lst:
        for author in paper_author:
            for another_author in paper_author:
                if author != another_author:
                    try:
                        g[author][another_author]['weight'] += (.5 / (len(paper_author) - 1))
                    except KeyError:
                        g.add_weighted_edges_from(
                            [[author, another_author, (.5 / (len(paper_author) - 1))]]
                        )

    edge_list = [[u, v, w['weight']] for (u, v, w) in g.edges(data=True) if w['weight'] >= min_weight]
    nodes = set([u for (u, v, w) in edge_list]).union(set([v for (u, v, w) in edge_list]))
    degrees = [d for (u, d) in g.degree(nbunch=list(nodes), weight='weight')]

    percentage_names = None

    if frequent_co_authors is not None and show_percentage_names == 0:
        percentage_names = frequent_co_authors

    elif frequent_co_authors is None and show_percentage_names != 0:
        cutoff_count = max(1, int(len(degrees) * (show_percentage_names / 100)))
        if len(degrees) == 0:
            percentage_names = []
            print("No node names will be shown (empty graph).")
        else:
            sorted_degrees = sorted(degrees, reverse=True)
            cutoff_count = min(cutoff_count, len(sorted_degrees))
            min_percentage_weight = sorted_degrees[:cutoff_count][-1]
            percentage_names = [
                u for (u, d) in g.degree(nbunch=list(nodes), weight='weight') if d >= min_percentage_weight
            ]
            print('The webpage will show the following {} names by default:'.format(len(percentage_names)))
            print('\t' + ', '.join(sorted(percentage_names, key=lambda name: name.split(' ')[-1])))

    elif frequent_co_authors is None and show_percentage_names == 0:
        percentage_names = None

    else:
        print("Either set 'frequent_co_authors' or a percentage, not both.")
        exit()

    return edge_list, percentage_names


def read_and_write_html(path):
    with open(path, 'r') as f:
        html_file = f.read()
        start_idx = html_file.index('<script type="text/javascript">var wwdata')
        end_idx = html_file.index('</script>', start_idx) + 9
        html_data = html_file[start_idx:end_idx]

    with open('./template.html', 'r') as f:
        html_file = f.read()
        start_idx = html_file.index('<script\n        type="text/javascript">var wwdata')
        end_idx = html_file.index('</script>', start_idx) + 9
        html_final = html_file.replace(html_file[start_idx:end_idx], html_data)

    with open(path, 'w') as f:
        f.write(html_final)


def main(fre_co_authors=None):
    f_ext = args.file.split('.')[-1]
    if f_ext == 'xml':
        co_author_lst = load_dblp_xml(path=args.file)
    elif f_ext in ['bib', 'txt']:
        co_author_lst = load_bib(path=args.file)
    else:
        print("Wrong file format. Use '.bib', '.xml', or '.txt'")
        exit()

    edge_list, percentage_names = build_graph(
        co_author_lst,
        args.min_edge_weight,
        frequent_co_authors=fre_co_authors,
        show_percentage_names=args.show_percentage_names
    )

    number_co_authors = len(set([u for (u, v, w) in edge_list] + [v for (u, v, w) in edge_list]))    
    web = Web(title=args.name_to_match)

    web.networks.xovee(adjacency=edge_list)

    web.display.colorBy = args.color_by
    web.display.sizeBy = args.size_by
    web.display.charge = args.charge
    web.display.linkLength = args.link_length
    web.display.scaleLinkOpacity = args.scale_link_opacity
    web.display.scaleLinkWidth = args.scale_link_width
    web.display.nameToMatch = args.name_to_match
    web.display.radius = args.radius
    web.display.showNodeNames = args.show_node_names
    web.display.hideMenu = args.hide_menu
    web.display.showLegend = args.show_legend
    web.display.frequentCoAuthors = percentage_names
    web.display.h = args.canvas_height
    web.display.w = args.canvas_width
    web.display.numberCoAuthor = number_co_authors
    web.display.displayName = args.display_name

    web.save(args.file.split('.')[0] + '.html')
    read_and_write_html(args.file.split('.')[0] + '.html')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='CANV Descriptions')

    parser.add_argument('file', type=str, help='Name of the data file.')
    parser.add_argument('--data', default='xml', type=str, choices=['bib', 'xml'], help='Type of the data file.')
    parser.add_argument('--display_name', default='Khan', type=str, help='The name displayed on the webpage.')
    parser.add_argument('--min_edge_weight', default=0, type=float, help='Edge weight less than this will be removed.')
    parser.add_argument('--color_by', default='strength', type=str, choices=['degree', 'strength'], help='Color nodes by.')
    parser.add_argument('--size_by', default='strength', type=str, choices=['degree', 'strength'], help='Size nodes by.')
    parser.add_argument('--charge', default=256, type=int, help='Charge of the graph.')
    parser.add_argument('--link_length', default=200, type=int, help='Length of the links.')
    parser.add_argument('--scale_link_opacity', default=1, type=int, help='Scale link opacity.')
    parser.add_argument('--scale_link_width', default=1, type=int, help='Scale link width.')
    parser.add_argument('--name_to_match', default='', type=str, help='Show a specific node name.')
    parser.add_argument('--radius', default=15, type=int, help='Radius.')
    parser.add_argument('--show_node_names', default=0, type=int, help='Whether show all node names in default.')
    parser.add_argument('--hide_menu', default=1, type=int, help='Whether hide the webpage menu.')
    parser.add_argument('--show_legend', default=0, type=int, help='Whether show the legend of canvas.')
    parser.add_argument('--show_percentage_names', default=10, type=int, help='Percentage of frequent names to show.')
    parser.add_argument('--canvas_height', default=700, type=float, help='Height of the canvas.')
    parser.add_argument('--canvas_width', default=1000, type=float, help='Width of the canvas.')

    args = parser.parse_args()

    main(fre_co_authors=None)
