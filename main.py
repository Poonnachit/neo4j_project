#! /usr/bin/env python3
"""
64160038 Poonnachit Amnuaypornpaisal
"""
import neo4j
import math


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
                print(f"You choose {choice} is '{choice_data[choice - 1]}'\n")
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
    create_constraint_cypher = "CREATE CONSTRAINT nodes_are_unique IF NOT EXISTS FOR (p:Place) REQUIRE (p.name) IS UNIQUE;"
    retval = query_void(driver=driver, the_cypher=create_constraint_cypher)
    if retval == EXIT_FAILURE:
        return EXIT_FAILURE

    create_constraint_cypher2 = "CREATE CONSTRAINT relation_are_unique IF NOT EXISTS FOR ()-[r:CONNECTS_TO]-() REQUIRE (r.name) IS UNIQUE;"
    retval = query_void(driver=driver, the_cypher=create_constraint_cypher2)
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


def add_road(*, driver):
    print("Add new road")

    start_node = select_place(title="Select start node", driver=driver)

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

    if have_end_node:
        if start_node == end_node:
            print("Start place and end place must be different.")
            return EXIT_FAILURE

    print("Road information")
    print("start:", start_node)
    if have_end_node:
        print("end:", end_node)
    while True:
        node_name = input("Enter Node name: ")
        if node_name == "":
            print("Node name cannot be empty.")
            continue
        break

    while True:
        node_latitude = input("Enter Node latitude: ")
        if node_latitude == "":
            print("Node latitude cannot be empty.")
            continue
        if node_latitude[0] == "-":
            if not node_latitude[1:].isdigit():
                print("Node latitude must be a number.")
                continue
        else:
            if not node_latitude.isdigit():
                print("Node latitude must be a number.")
                continue
        break

    while True:
        node_longitude = input("Enter Node longitude: ")
        if node_longitude == "":
            print("Node longitude cannot be empty.")
            continue
        if node_longitude[0] == "-":
            if not node_longitude[1:].isdigit():
                print("Node longitude must be a number.")
                continue
        else:
            if not node_longitude.isdigit():
                print("Node longitude must be a number.")
                continue
        break

    while True:
        node_light = input("Enter node light (Yes/No): ")
        if node_light == "":
            print("node light cannot be empty.")
            continue
        if node_light not in ["Yes", "No", "yes", "no", "y", "n"]:
            print("node light must be 'Yes' or 'No'.")
            continue
        if node_light == "Yes" or node_light == "yes" or node_light == "y":
            node_light = True
        else:
            node_light = False
        break

    while True:
        road_name_from_start = input("Enter road name from start: ")
        if road_name_from_start == "":
            print("Road name from start cannot be empty.")
            continue
        break

    while True:
        road_distance_from_start = input("Enter road distance from start: ")
        if road_distance_from_start == "":
            print("Road distance from start cannot be empty.")
            continue
        elif not road_distance_from_start.isdigit():
            print("Road distance from start must be a number.")
            continue
        break

    create_node_with_relation_template = (
        "MATCH (n:Place) WHERE n.name = '{}'"
        "MERGE (m:Place {{name: '{}', latitude: {}, longitude: {}, light: {}}})"
        "CREATE (n)-[:CONNECTS_TO {{name: '{}', distance: {}}}]->(m)"
    )

    create_node_with_start_node = create_node_with_relation_template.format(
        start_node,
        node_name,
        node_latitude,
        node_longitude,
        node_light,
        road_name_from_start,
        road_distance_from_start,
    )

    retval = query_void(driver=driver, the_cypher=create_node_with_start_node)
    if retval == EXIT_FAILURE:
        print("Failed to create node with start node.")
        return EXIT_FAILURE

    if have_end_node:
        while True:
            road_name_from_end = input("Enter road name from end: ")
            if road_name_from_end == "":
                print("Road name from end cannot be empty.")
                continue
            break

        while True:
            road_distance_from_end = input("Enter road distance from end: ")
            if road_distance_from_end == "":
                print("Road distance from end cannot be empty.")
                continue
            elif not road_distance_from_end.isdigit():
                print("Road distance from end must be a number.")
                continue
            break

        create_node_with_end_node = create_node_with_relation_template.format(
            end_node,
            node_name,
            node_latitude,
            node_longitude,
            node_light,
            road_name_from_end,
            road_distance_from_end,
        )

        retval = query_void(driver=driver, the_cypher=create_node_with_end_node)
        if retval == EXIT_FAILURE:
            print("Failed to create node with end node.")
            return EXIT_FAILURE

    return EXIT_SUCCESS


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
                        "Show all places",
                        "Add new road",
                        "Add new intersect",
                        "Exit",
                    ]
                )
                match choice:
                    case "Show all places":
                        select_place(driver=driver)
                    case "Add new road":
                        add_road(driver=driver)
                    case "Add new intersect":
                        pass
                    case "Exit":
                        return EXIT_SUCCESS

    except neo4j.exceptions.ServiceUnavailable:
        print("Database service is not available.")
        return EXIT_FAILURE
    except KeyboardInterrupt:
        print("User Exit Ctrl-C")
        return EXIT_SUCCESS


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
