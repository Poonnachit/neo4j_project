#! /usr/bin/env python3
"""
64160038 Poonnachit Amnuaypornpaisal
"""
import neo4j
import math


def is_float(value):
    try:
        float(value)
        return True
    except ValueError:
        return False


def get_compass_direction(*, vector):
    numerator = vector[1][1] - vector[0][1]
    denominator = vector[1][0] - vector[0][0]
    if denominator == 0:
        if numerator >= 0:
            angle = 90
        else:
            angle = 270
    elif numerator == 0:
        if denominator >= 0:
            angle = 0
        else:
            angle = 180
    else:
        fraction = numerator / denominator
        # get angle in degrees
        fvalue = math.degrees(math.atan(fraction))
        # magic.... to get rounding right
        angle = int(math.ceil(round(fvalue, 1)))
        # adjust for quadrant if not quadrant I
        if denominator < 0:  # quadrants II & III
            angle += 180
        elif numerator < 0:  # quadrant IV
            angle += 360
    slot_no = (angle - HALF_SLOT_SIZE) // SLOT_SIZE  # rotate CLOCKWISE half_slot_size
    # that might move 1/2 of the "E" negative, so fix that special case
    if slot_no < 0:
        slot_no = 0.0  # fix the special case
    else:
        slot_no += 1.0  # remember, rotate CLOCKWISE by 1
    slot_no = int(slot_no) % POINT_COUNT
    try:
        retval = DIRECTIONS[slot_no]
        return retval
    except IndexError as err_msg:
        print(f"slot_no={slot_no:d}, angle={angle:f}:{str(err_msg)}")


def get_choice(*, msg="Please enter choice: ", choice_data):
    max_len = len(choice_data)
    while True:
        for numb, data in enumerate(choice_data, start=1):
            print(f"{numb}. {data}")
        try:
            choice = int(input(f"{msg}"))
            if max_len >= choice > 0:
                print(f"You choose {choice} is '{choice_data[choice - 1]}'")
                return choice_data[choice - 1]
            else:
                raise ValueError("Invalid input")
        except (ValueError, EOFError):
            print("-" * 79)
            print(f"Please enter a valid choice.(between 1-{max_len})")


def print_error(*, the_cypher, bad_news, records, summary):
    print(the_cypher)
    print("Oh no:")
    for item_no, item in enumerate(bad_news, start=1):
        print(item_no, item)
    print("records:", records)
    print("summary.result_available_after:", summary.result_available_after)
    print("summary.summary_notifications:", summary.summary_notifications)


def query_void(*, driver, the_cypher):
    """For Cypher code that does not return anything normally"""
    try:
        records, summary, keys = driver.execute_query(the_cypher, database_=DBNAME)
        if summary.notifications is not None:
            bad_news = []
            for item in summary.notifications:
                if item["severity"] != "INFORMATION":  # ignore
                    bad_news.append(item)
            if len(bad_news) == 0:  # hey, no problems we care about
                return EXIT_SUCCESS
            # we have any bad news
            print_error(
                the_cypher=the_cypher,
                bad_news=bad_news,
                records=records,
                summary=summary,
            )
            return EXIT_FAILURE
    except neo4j.exceptions.ClientError as err_msg:
        if err_msg.code == "Neo.ClientError.Schema.ConstraintValidationFailed":
            return EXIT_SUCCESS
        # print(the_cypher)
        print(err_msg.code)
        return EXIT_FAILURE
    return EXIT_SUCCESS


def query(*, driver, the_cypher):
    """For Cypher code that does return something normally"""
    try:
        records, summary, keys = driver.execute_query(the_cypher, database_=DBNAME)
        if summary.notifications is not None:
            bad_news = []
            for item in summary.notifications:
                if item["severity"] != "INFORMATION":  # ignore
                    bad_news.append(item)
            if len(bad_news) == 0:  # hey, no problems we care about
                return EXIT_SUCCESS, records, summary, keys
            # we have any bad news
            print_error(
                the_cypher=the_cypher,
                bad_news=bad_news,
                records=records,
                summary=summary,
            )
            return EXIT_FAILURE, None, None, None
    except neo4j.exceptions.ClientError as err_msg:
        print(the_cypher)
        print(err_msg)
        return EXIT_FAILURE, None, None, None
    return EXIT_SUCCESS, records, summary, keys


def create_constraint(*, driver):
    create_constraint_cypher = (
        "CREATE CONSTRAINT nodes_are_unique IF NOT EXISTS "
        "FOR (p:Place) REQUIRE (p.name) IS UNIQUE;"
    )
    retval = query_void(driver=driver, the_cypher=create_constraint_cypher)
    if retval == EXIT_FAILURE:
        return EXIT_FAILURE

    return EXIT_SUCCESS


def create_index(*, driver):
    create_index_cypher = (
        "CREATE INDEX name_index IF NOT EXISTS FOR (p:Place) ON (p.name);"
    )

    retval = query_void(driver=driver, the_cypher=create_index_cypher)
    if retval == EXIT_FAILURE:
        return EXIT_FAILURE

    create_index_cypher2 = "CREATE INDEX relation_index IF NOT EXISTS FOR ()-[r:CONNECTS_TO]-() ON (r.name);"
    retval = query_void(driver=driver, the_cypher=create_index_cypher2)
    if retval == EXIT_FAILURE:
        return EXIT_FAILURE

    return EXIT_SUCCESS


def bulk_insert(*, driver):

    delete_all = "MATCH (N) DETACH DELETE N"
    retval = query_void(driver=driver, the_cypher=delete_all)
    if retval == EXIT_FAILURE:
        return EXIT_FAILURE

    with open("bangsean_data.txt", "r") as f:
        data = f.read()
        retval = query_void(driver=driver, the_cypher=data)
        if retval == EXIT_FAILURE:
            return EXIT_FAILURE
    return EXIT_SUCCESS


def select_place(*, driver, title="Select place"):
    count_place_node = "MATCH (n:Place) RETURN count(n)"
    retval, records, summary, keys = query(driver=driver, the_cypher=count_place_node)
    if retval == EXIT_FAILURE:
        return EXIT_FAILURE

    per_page = 3
    skip = 0
    total_place = records[0].data()["count(n)"]

    while True:
        print(title)
        get_all_places = (
            f"MATCH (n:Place) RETURN n ORDER BY n.name SKIP {skip} LIMIT {per_page}"
        )
        retval, records, summary, keys = query(driver=driver, the_cypher=get_all_places)
        if retval == EXIT_FAILURE:
            return EXIT_FAILURE

        nodes_name = [i.data()["n"]["name"] for i in records]

        if skip + per_page < total_place:
            nodes_name.append("Next")
        if skip > 0:
            nodes_name.append("Previous")

        selected_node = get_choice(choice_data=nodes_name)

        match selected_node:
            case "Next":
                skip += per_page
            case "Previous":
                skip -= per_page
            case _:
                return selected_node


def node_name_input():
    while True:
        node_name = input("Enter Node name: ")
        if node_name == "":
            print("Node name cannot be empty.")
            continue
        break
    return node_name


def node_latitude_input():
    while True:
        node_latitude = input("Enter Node latitude: ")
        if node_latitude == "":
            print("Node latitude cannot be empty.")
            continue
        if node_latitude[0] == "-":
            if not is_float(node_latitude[1:]):
                print("Node latitude must be a number.")
                continue
        else:
            if not is_float(node_latitude):
                print("Node latitude must be a number.")
                continue
        break
    return node_latitude


def node_longitude_input():
    while True:
        node_longitude = input("Enter Node longitude: ")
        if node_longitude == "":
            print("Node longitude cannot be empty.")
            continue
        if node_longitude[0] == "-":
            if not is_float(node_longitude[1:]):
                print("Node longitude must be a number.")
                continue
        else:
            if not is_float(node_longitude.isdigit()):
                print("Node longitude must be a number.")
                continue
        break
    return node_longitude


def node_light_input():
    while True:
        node_light = input("Enter Node light (Yes/No): ")
        if node_light == "":
            print("Node light cannot be empty.")
            continue
        if node_light not in ["Yes", "No", "yes", "no", "y", "n"]:
            print("Node light must be 'Yes' or 'No'.")
            continue
        if node_light == "Yes" or node_light == "yes" or node_light == "y":
            node_light = True
        else:
            node_light = False
        break
    return node_light


def road_name_input():
    while True:
        road_name = input("Enter Road name: ")
        if road_name == "":
            print("Road name cannot be empty.")
            continue
        break
    return road_name


def road_distance_input():
    while True:
        road_distance = input("Enter Road distance: ")
        if road_distance == "":
            print("Road distance cannot be empty.")
            continue
        elif not road_distance.isdigit():
            print("Road distance must be a number.")
            continue
        break
    return road_distance


def add_road(*, driver):

    print("Add new road")
    node_name = node_name_input()
    node_latitude = node_latitude_input()
    node_longitude = node_longitude_input()
    node_light = node_light_input()

    start_node = select_place(title="Select start node", driver=driver)
    road_name_from_start = road_name_input()
    road_distance_from_start = road_distance_input()
    create_node_with_start_node = CREATE_NODE_WITH_RELATION.format(
        start_node,
        node_name,
        node_latitude,
        node_longitude,
        node_light,
        road_name_from_start,
        road_distance_from_start,
        road_name_from_start,
        road_distance_from_start,
    )
    retval = query_void(driver=driver, the_cypher=create_node_with_start_node)
    if retval == EXIT_FAILURE:
        print("Failed to create node with start node.")
        return EXIT_FAILURE

    while True:
        have_end_node = input("Do you have end node? (Yes/No): ")
        if have_end_node == "":
            print("Have end node cannot be empty.")
            continue
        if have_end_node not in ["Yes", "No", "yes", "no", "y", "n"]:
            print("Have end node must be 'Yes' or 'No'.")
            continue
        if have_end_node == "Yes" or have_end_node == "yes" or have_end_node == "y":
            have_end_node = True
        else:
            have_end_node = False
        break

    if have_end_node:
        end_node = select_place(title="Select end node", driver=driver)
        if start_node == end_node:
            print("Start place and end place must be different.")
            return EXIT_FAILURE
        road_name_from_end = road_name_input()
        road_distance_from_end = road_distance_input()
        create_node_with_end_node = CREATE_NODE_WITH_RELATION.format(
            end_node,
            node_name,
            node_latitude,
            node_longitude,
            node_light,
            road_name_from_end,
            road_distance_from_end,
            road_name_from_end,
            road_distance_from_end,
        )
        retval = query_void(driver=driver, the_cypher=create_node_with_end_node)
        if retval == EXIT_FAILURE:
            print("Failed to create node with end node.")
            return EXIT_FAILURE
    return EXIT_SUCCESS


def add_intersect(*, driver):
    print("Add new intersect")
    node_name = node_name_input()
    node_latitude = node_latitude_input()
    node_longitude = node_longitude_input()
    node_light = node_light_input()

    start_node = select_place(title="Select start node", driver=driver)
    road_name_from_start = road_name_input()
    road_distance_from_start = road_distance_input()

    end_node = select_place(title="Select end node", driver=driver)
    if start_node == end_node:
        print("Start place and end place must be different.")
        return EXIT_FAILURE
    road_name_from_end = road_name_input()
    road_distance_from_end = road_distance_input()

    delete_old_relation = "MATCH (n:Place {{name: '{}'}})-[r:CONNECTS_TO]-(m:Place {{name: '{}'}}) DELETE r"
    retval = query_void(
        driver=driver, the_cypher=delete_old_relation.format(start_node, end_node)
    )
    if retval == EXIT_FAILURE:
        print("Failed to delete old relation.")
        return EXIT_FAILURE

    create_node_with_start_node = CREATE_NODE_WITH_RELATION.format(
        start_node,
        node_name,
        node_latitude,
        node_longitude,
        node_light,
        road_name_from_start,
        road_distance_from_start,
        road_name_from_start,
        road_distance_from_start,
    )
    retval = query_void(driver=driver, the_cypher=create_node_with_start_node)
    if retval == EXIT_FAILURE:
        print("Failed to create node with start node.")
        return EXIT_FAILURE

    create_node_with_end_node = CREATE_NODE_WITH_RELATION.format(
        end_node,
        node_name,
        node_latitude,
        node_longitude,
        node_light,
        road_name_from_end,
        road_distance_from_end,
        road_name_from_end,
        road_distance_from_end,
    )
    retval = query_void(driver=driver, the_cypher=create_node_with_end_node)
    if retval == EXIT_FAILURE:
        print("Failed to create node with end node.")
        return EXIT_FAILURE

    return EXIT_SUCCESS


def delete_node(*, driver):
    selected_node = select_place(title="Select node to delete", driver=driver)

    check_node = (
        "MATCH (n:Place {{name: '{}'}})-[r:CONNECTS_TO]-(m:Place) RETURN DISTINCT m"
    )

    retval, records, summary, keys = query(
        driver=driver, the_cypher=check_node.format(selected_node)
    )
    if retval == EXIT_FAILURE:
        return EXIT_FAILURE

    related_nodes = [i.data()["m"]["name"] for i in records]

    distance_dict = {}
    distance_cypher = "MATCH (n:Place {{name: '{}'}})-[r:CONNECTS_TO]-(m:Place {{name: '{}'}}) RETURN r.distance"
    for node in related_nodes:
        retval, records, summary, keys = query(
            driver=driver, the_cypher=distance_cypher.format(selected_node, node)
        )
        if retval == EXIT_FAILURE:
            return EXIT_FAILURE
        distance_dict[node] = records[0].data()["r.distance"]

    pair_related_nodes = []
    for i in range(len(related_nodes)):
        for j in range(i + 1, len(related_nodes)):
            pair_related_nodes.append((related_nodes[i], related_nodes[j]))

    for pair in pair_related_nodes:
        start_node = pair[0]
        end_node = pair[1]
        total_distance = distance_dict[start_node] + distance_dict[end_node]

        check_exist_relation = "MATCH (n:Place {{name: '{}'}})-[r:CONNECTS_TO]-(m:Place {{name: '{}'}}) RETURN count(r)"
        retval, records, summary, keys = query(
            driver=driver, the_cypher=check_exist_relation.format(start_node, end_node)
        )
        if retval == EXIT_FAILURE:
            return EXIT_FAILURE

        if records[0].data()["count(r)"] == 0:
            create_relation = (
                "MATCH (n:Place) WHERE n.name = '{}' "
                "MATCH (m:Place) WHERE m.name = '{}' "
                "CREATE (n)-[:CONNECTS_TO {{name: '{}', distance: {}}}]->(m),"
                "(m)-[:CONNECTS_TO {{name: '{}', distance: {}}}]->(n)"
            )

            retval = query_void(
                driver=driver,
                the_cypher=create_relation.format(
                    start_node,
                    end_node,
                    f"{start_node} to {end_node}",
                    total_distance,
                    f"{start_node} to {end_node}",
                    total_distance,
                ),
            )
            if retval == EXIT_FAILURE:
                print("Failed to create relation.")
                return EXIT_FAILURE

    delete_node_cypher = "MATCH (n:Place {{name: '{}'}}) DETACH DELETE n"
    retval = query_void(
        driver=driver, the_cypher=delete_node_cypher.format(selected_node)
    )
    if retval == EXIT_FAILURE:
        print("Failed to delete node.")
        return EXIT_FAILURE

    return EXIT_SUCCESS


def edit_node_name(*, driver, selected_node):
    edit_node_name_cypher = "MATCH (n:Place {{name: '{}'}}) SET n.name = '{}'"
    node_name = node_name_input()
    retval = query_void(
        driver=driver, the_cypher=edit_node_name_cypher.format(selected_node, node_name)
    )
    if retval == EXIT_FAILURE:
        print("Failed to edit node name.")
        return EXIT_FAILURE
    return EXIT_SUCCESS


def edit_node_latitude(*, driver, selected_node):
    edit_node_latitude_cypher = "MATCH (n:Place {{name: '{}'}}) SET n.latitude = {}"
    node_latitude = node_latitude_input()
    retval = query_void(
        driver=driver,
        the_cypher=edit_node_latitude_cypher.format(selected_node, node_latitude),
    )
    if retval == EXIT_FAILURE:
        print("Failed to edit node latitude.")
        return EXIT_FAILURE
    return EXIT_SUCCESS


def edit_node_longitude(*, driver, selected_node):
    edit_node_longitude_cypher = "MATCH (n:Place {{name: '{}'}}) SET n.longitude = {}"
    node_longitude = node_longitude_input()
    retval = query_void(
        driver=driver,
        the_cypher=edit_node_longitude_cypher.format(selected_node, node_longitude),
    )
    if retval == EXIT_FAILURE:
        print("Failed to edit node longitude.")
        return EXIT_FAILURE
    return EXIT_SUCCESS


def edit_node_light(*, driver, selected_node):
    edit_node_light_cypher = "MATCH (n:Place {{name: '{}'}}) SET n.light = {}"
    node_light = node_light_input()
    retval = query_void(
        driver=driver,
        the_cypher=edit_node_light_cypher.format(selected_node, node_light),
    )
    if retval == EXIT_FAILURE:
        print("Failed to edit node light.")
        return EXIT_FAILURE
    return EXIT_SUCCESS


def print_node_properties(*, driver, selected_node):
    get_node_properties = "MATCH (n:Place {{name: '{}'}}) RETURN n"
    retval, records, summary, keys = query(
        driver=driver, the_cypher=get_node_properties.format(selected_node)
    )
    if retval == EXIT_FAILURE:
        return EXIT_FAILURE

    node = records[0].data()["n"]
    print("Current properties")
    print(f"Name     : {node['name']}")
    print(f"Latitude : {node['latitude']}")
    print(f"Longitude: {node['longitude']}")
    print(f"Light    : {node['light']}")
    print("-" * 79)
    return EXIT_SUCCESS


def edit_node_properties(*, driver, selected_node):
    retval = print_node_properties(driver=driver, selected_node=selected_node)
    if retval == EXIT_FAILURE:
        return EXIT_FAILURE

    selected_property = get_choice(
        msg="Please enter property to edit: ",
        choice_data=["Name", "Latitude", "Longitude", "Light"],
    )
    match selected_property:
        case "Name":
            retval = edit_node_name(driver=driver, selected_node=selected_node)
            if retval == EXIT_FAILURE:
                print("Failed to edit name.")
                return EXIT_FAILURE
        case "Latitude":
            retval = edit_node_latitude(driver=driver, selected_node=selected_node)
            if retval == EXIT_FAILURE:
                print("Failed to edit latitude.")
                return EXIT_FAILURE
        case "Longitude":
            retval = edit_node_longitude(driver=driver, selected_node=selected_node)
            if retval == EXIT_FAILURE:
                print("Failed to edit longitude.")
                return EXIT_FAILURE
        case "Light":
            retval = edit_node_light(driver=driver, selected_node=selected_node)
            if retval == EXIT_FAILURE:
                print("Failed to edit light.")
                return EXIT_FAILURE
    return EXIT_SUCCESS


def edit_relation_name(*, driver, node1, node2):
    edit_relation_name_cypher = "MATCH (n:Place {{name: '{}'}})-[r:CONNECTS_TO]-(m:Place {{name: '{}'}}) SET r.name = '{}'"
    new_name = input("Enter new name: ")
    retval = query_void(
        driver=driver,
        the_cypher=edit_relation_name_cypher.format(node1, node2, new_name),
    )
    if retval == EXIT_FAILURE:
        print("Failed to edit relation name.")
        return EXIT_FAILURE
    return EXIT_SUCCESS


def edit_relation_distance(*, driver, node1, node2):
    edit_relation_distance_cypher = (
        "MATCH (n:Place {{name: '{}'}})-[r:CONNECTS_TO]-(m:Place {{name: '{}'}}) "
        "SET r.distance = {}"
    )
    new_distance = input("Enter new distance: ")
    retval = query_void(
        driver=driver,
        the_cypher=edit_relation_distance_cypher.format(node1, node2, new_distance),
    )
    if retval == EXIT_FAILURE:
        print("Failed to edit relation distance.")
        return EXIT_FAILURE
    return EXIT_SUCCESS


def edit_relation_properties(*, driver, selected_node):
    related_nodes_cypher = (
        "MATCH (n:Place {{name: '{}'}})-[r:CONNECTS_TO]-(m:Place) RETURN DISTINCT m"
    )
    retval, records, summary, keys = query(
        driver=driver, the_cypher=related_nodes_cypher.format(selected_node)
    )
    if retval == EXIT_FAILURE:
        return EXIT_FAILURE

    related_nodes = [i.data()["m"]["name"] for i in records]
    selected_related_node = get_choice(
        msg="Please enter related node to edit: ", choice_data=related_nodes
    )

    relation_detail_cypher = (
        "MATCH (n:Place {{name: '{}'}})-[r:CONNECTS_TO]-(m:Place {{name: '{}'}}) "
        "RETURN r.name, r.distance"
    )
    retval, records, summary, keys = query(
        driver=driver,
        the_cypher=relation_detail_cypher.format(selected_node, selected_related_node),
    )
    if retval == EXIT_FAILURE:
        return EXIT_FAILURE

    relation = records[0].data()
    print(relation)
    print("Current properties")
    print(f"Name    : {relation['r.name']}")
    print(f"Distance: {relation['r.distance']}")
    print("-" * 79)

    selected_property = get_choice(
        msg="Please enter property to edit: ", choice_data=["Name", "Distance"]
    )
    match selected_property:
        case "Name":
            retval = edit_relation_name(
                driver=driver, node1=selected_node, node2=selected_related_node
            )
            if retval == EXIT_FAILURE:
                print("Failed to edit relation name.")
                return EXIT_FAILURE
        case "Distance":
            print("Edit distance")
    return EXIT_SUCCESS


def add_relation(*, driver, selected_node):
    not_related_nodes_cypher = (
        "MATCH (n:Place)"
        "WHERE NOT (n)-[:CONNECTS_TO]-(:Place {{name: '{}'}})"
        "RETURN n.name"
    )
    retval, records, summary, keys = query(
        driver=driver, the_cypher=not_related_nodes_cypher.format(selected_node)
    )
    if retval == EXIT_FAILURE:
        return EXIT_FAILURE

    not_related_nodes = [
        record.data()["n.name"]
        for record in records
        if record.data()["n.name"] != selected_node
    ]

    if len(not_related_nodes) == 0:
        print("No node that not related to this node")
        return EXIT_SUCCESS

    selected_related_node = get_choice(
        msg="Please enter what your want to connect with: ",
        choice_data=not_related_nodes,
    )

    road_name = road_name_input()
    road_distance = road_distance_input()

    create_relation_cypher = (
        "MATCH (n:Place {{name: '{}'}}), (m:Place {{name: '{}'}})"
        "CREATE (n)-[:CONNECTS_TO {{name: '{}', distance: {}}}]->(m),"
        "(m)-[:CONNECTS_TO {{name: '{}', distance: {}}}]->(n)"
    )

    retval = query_void(
        driver=driver,
        the_cypher=create_relation_cypher.format(
            selected_node,
            selected_related_node,
            road_name,
            road_distance,
            road_name,
            road_distance,
        ),
    )
    if retval == EXIT_FAILURE:
        print("Failed to create relation.")
        return EXIT_FAILURE
    return EXIT_SUCCESS


def delete_relation(*, driver, selected_node):
    related_nodes_cypher = (
        "MATCH (n:Place {{name: '{}'}})-[r:CONNECTS_TO]-(m:Place) RETURN DISTINCT m"
    )
    retval, records, summary, keys = query(
        driver=driver, the_cypher=related_nodes_cypher.format(selected_node)
    )
    if retval == EXIT_FAILURE:
        return EXIT_FAILURE

    related_nodes = [i.data()["m"]["name"] for i in records]
    selected_related_node = get_choice(
        msg="Please enter related node to delete: ", choice_data=related_nodes
    )

    while True:
        confirm = input("Are you sure to delete this relation? (Yes/No): ")
        if confirm == "":
            print("Confirm cannot be empty.")
            continue
        if confirm not in ["Yes", "No", "yes", "no", "y", "n"]:
            print("Confirm must be 'Yes' or 'No'.")
            continue
        if confirm == "Yes" or confirm == "yes" or confirm == "y":
            confirm = True
        else:
            confirm = False
        break

    if not confirm:
        return EXIT_SUCCESS

    delete_relation_cypher = "MATCH (n:Place {{name: '{}'}})-[r:CONNECTS_TO]-(m:Place {{name: '{}'}}) DELETE r"
    retval = query_void(
        driver=driver,
        the_cypher=delete_relation_cypher.format(selected_node, selected_related_node),
    )
    if retval == EXIT_FAILURE:
        print("Failed to delete relation.")
        return EXIT_FAILURE
    return EXIT_SUCCESS


def relation_properties_menu(*, driver, selected_node):
    selected_action = get_choice(
        msg="Please enter action: ", choice_data=["Add", "Edit", "Delete"]
    )

    match selected_action:
        case "Add":
            add_relation(driver=driver, selected_node=selected_node)
        case "Edit":
            edit_relation_properties(driver=driver, selected_node=selected_node)
        case "Delete":
            delete_relation(driver=driver, selected_node=selected_node)


def edit_properties(*, driver):
    selected_place = select_place(
        title="Select place to edit properties", driver=driver
    )

    print(f"Edit properties of {selected_place}")
    selected_edit = get_choice(
        msg="Please enter edit: ", choice_data=["Node", "Relation", "Exit"]
    )
    match selected_edit:
        case "Node":
            edit_node_properties(driver=driver, selected_node=selected_place)
        case "Relation":
            relation_properties_menu(driver=driver, selected_node=selected_place)
        case "Exit":
            return EXIT_SUCCESS
    return EXIT_SUCCESS


def print_shortest_path(*, lst, driver):
    # lst = [("A", "B"), ("B", "C"), ("C", "D")]
    for i in range(len(lst)):
        if i == 0:
            print(f"Shortest path from {lst[i][0]} to {lst[-1][1]}")
            print(f"Start at {lst[i][0]}")

        node_data = "MATCH (n:Place {{name: '{}'}}), (m:Place {{name:'{}'}}) RETURN n,m"
        retval, records, summary, keys = query(
            driver=driver, the_cypher=node_data.format(lst[i][0], lst[i][1])
        )
        if retval == EXIT_FAILURE:
            return EXIT_FAILURE

        result = records[0].data()
        n, m = result["n"], result["m"]
        vector = [(n["longitude"], n["latitude"]), (m["longitude"], m["latitude"])]
        direction = get_compass_direction(vector=vector)

        relation_data = "MATCH (n:Place {{name: '{}'}})-[r:CONNECTS_TO]-(m:Place {{name: '{}'}}) RETURN r.name, r.distance"
        retval, records, summary, keys = query(
            driver=driver, the_cypher=relation_data.format(lst[i][0], lst[i][1])
        )
        if retval == EXIT_FAILURE:
            return EXIT_FAILURE

        relation = records[0].data()
        print(f"Head {direction}")
        print(
            f"then go to {lst[i][1]} on {relation['r.name']} ({relation['r.distance']} km)",
            end=" ",
        )
        if m["light"]:
            print("stop at traffic light")
        else:
            print("no traffic light")
        if i == len(lst) - 1:
            print(f"and you have arrived at at your destination {lst[i][1]}")


def get_shortest_path_by_distance(*, driver):
    start_node = select_place(title="Select start node", driver=driver)
    end_node = select_place(title="Select end node", driver=driver)
    if start_node == end_node:
        print("Start place and end place must be different.")
        return EXIT_FAILURE

    drop_graph = "CALL gds.graph.drop('myGraph', false) YIELD graphName;"
    retval = query_void(driver=driver, the_cypher=drop_graph)
    if retval == EXIT_FAILURE:
        print("Failed to drop graph.")
        return EXIT_FAILURE

    create_graph = """\
    CALL gds.graph.project(
        'myGraph',
        'Place',
        {CONNECTS_TO: {orientation: 'UNDIRECTED'}},
        {
            relationshipProperties: 'distance'
        }
    );
    """

    retval = query_void(driver=driver, the_cypher=create_graph)
    if retval == EXIT_FAILURE:
        print("Failed to create graph.")
        return EXIT_FAILURE

    dijkstra_cypher = """
    MATCH (source:Place {{name: '{}'}}), (target:Place {{name: '{}'}})
    CALL gds.shortestPath.dijkstra.stream('myGraph', {{
        sourceNode: source,
        targetNode: target,
        relationshipWeightProperty: 'distance'
    }})
    YIELD index, sourceNode, targetNode, totalCost, nodeIds, costs, path
    RETURN
        index,
        gds.util.asNode(sourceNode).name AS sourceNodeName,
        gds.util.asNode(targetNode).name AS targetNodeName,
        totalCost,
        [nodeId IN nodeIds | gds.util.asNode(nodeId).name] AS nodeNames,
        costs,
        nodes(path) as path
    ORDER BY index;
    """
    retval, records, summary, keys = query(
        driver=driver, the_cypher=dijkstra_cypher.format(start_node, end_node)
    )
    if retval == EXIT_FAILURE:
        return EXIT_FAILURE

    for record in records:
        data = record.data()["path"]
        name_lst = [i["name"] for i in data]

        bob = list(zip(name_lst, name_lst[1:]))
        print_shortest_path(driver=driver, lst=bob)


def get_shortest_path_by_node(*, driver):
    start_node = select_place(title="Select start node", driver=driver)
    end_node = select_place(title="Select end node", driver=driver)
    if start_node == end_node:
        print("Start place and end place must be different.")
        return EXIT_FAILURE

    cypher = """
    MATCH
      (start:Place {{name: '{}'}}),
      (end:Place {{name: '{}'}}),
      p = shortestPath((start)-[*]-(end))
    WHERE length(p) > 1
    RETURN p
    """
    retval, records, summary, keys = query(
        driver=driver, the_cypher=cypher.format(start_node, end_node)
    )
    if retval == EXIT_FAILURE:
        return EXIT_FAILURE

    for record in records:
        path = record.data()["p"]
        print("Shortest path:")

        node_names = []
        for i in range(len(path)):
            print(path[i])
            if i % 2 == 0:
                node_names.append(path[i]["name"])
        bob = list(zip(node_names, node_names[1:]))
        print_shortest_path(driver=driver, lst=bob)


def main():
    try:
        with neo4j.GraphDatabase.driver(URI, auth=AUTH) as driver:

            retval = create_constraint(driver=driver)
            if retval == EXIT_FAILURE:
                print("Failed to create constraint.")
                return EXIT_FAILURE

            retval = create_index(driver=driver)
            if retval == EXIT_FAILURE:
                print("Failed to create index.")
                return EXIT_FAILURE

            retval = bulk_insert(driver=driver)
            if retval == EXIT_FAILURE:
                print("Failed to insert data.")
                return EXIT_FAILURE

            while True:
                print("-" * 79)
                print("Main Menu")
                choice = get_choice(
                    choice_data=[
                        "Get the shortest path by distance",
                        "Get the shortest path by node",
                        "Add Node (Road)",
                        "Add Node (Intersect)",
                        "Edit Properties",
                        "Delete Node",
                        "Exit",
                    ]
                )
                match choice:
                    case "Get the shortest path by distance":
                        retval = get_shortest_path_by_distance(driver=driver)
                        if retval == EXIT_FAILURE:
                            print("Failed to get shortest path by distance.")
                            return EXIT_FAILURE
                    case "Get the shortest path by node":
                        retval = get_shortest_path_by_node(driver=driver)
                        if retval == EXIT_FAILURE:
                            print("Failed to get shortest path by node.")
                            return EXIT_FAILURE

                    case "Add Node (Road)":
                        retval = add_road(driver=driver)
                        if retval == EXIT_FAILURE:
                            print("Failed to add road.")
                            return EXIT_FAILURE
                    case "Add Node (Intersect)":
                        retval = add_intersect(driver=driver)
                        if retval == EXIT_FAILURE:
                            print("Failed to add intersect.")
                            return EXIT_FAILURE

                    case "Edit Properties":
                        retval = edit_properties(driver=driver)
                        if retval == EXIT_FAILURE:
                            print("Failed to edit properties.")
                            return EXIT_FAILURE

                    case "Delete Node":
                        retval = delete_node(driver=driver)
                        if retval == EXIT_FAILURE:
                            print("Failed to delete node.")
                            return EXIT_FAILURE
                    case "Exit":
                        return EXIT_SUCCESS

    except neo4j.exceptions.ServiceUnavailable:
        print("Database service is not available.")
        return EXIT_FAILURE
    except KeyboardInterrupt:
        print("User Exit Ctrl-C")
        return EXIT_SUCCESS


CREATE_NODE_WITH_RELATION = (
    "MATCH (n:Place) WHERE n.name = '{}'"
    "MERGE (m:Place {{name: '{}', latitude: {}, longitude: {}, light: {}}})"
    "CREATE (n)-[:CONNECTS_TO {{name: '{}', distance: {}}}]->(m),"
    "(m)-[:CONNECTS_TO {{name: '{}', distance: {}}}]->(n)"
)

DIRECTIONS = [
    "East",
    "East North East",
    "North East",
    "North North East",
    "North",
    "North North West",
    "North West",
    "West North West",
    "West",
    "West South West",
    "South West",
    "South South West",
    "South",
    "South South East",
    "South East",
    "East South East",
]
# number of directions (pie slices, points in compass rose)
POINT_COUNT = len(DIRECTIONS)
# map from angle in degrees to direction name
SLOT_SIZE = 360 / POINT_COUNT
HALF_SLOT_SIZE = SLOT_SIZE / 2  # amount to rotate CLOCKWISE
DBNAME = "neo4j"
URI, AUTH = "neo4j://localhost", ("neo4j", "64160038")
EXIT_SUCCESS, EXIT_FAILURE = 0, 1

if __name__ == "__main__":
    raise SystemExit(main())
