
import streamlit as st
import pandas as pd
import plotly.express as px
import folium
import requests
import math

from streamlit_folium import st_folium
from streamlit_geolocation import streamlit_geolocation
from geopy.geocoders import Nominatim
from datetime import date, timedelta

import database as db


# ==================================================
# PAGE CONFIGURATION
# ==================================================

st.set_page_config(
    page_title="Trip Planner",
    page_icon="✈️",
    layout="wide"
)


# ==================================================
# IMAGES
# ==================================================

DASHBOARD_IMAGE = (
    "https://images.unsplash.com/photo-1464822759023-fed622ff2c3b"
    "?auto=format&fit=crop&w=1800&q=85"
)

CREATE_TRIP_IMAGE = (
    "https://images.unsplash.com/photo-1501785888041-af3ef285b470"
    "?auto=format&fit=crop&w=900&q=85"
)

MY_TRIPS_IMAGE = (
    "https://images.unsplash.com/photo-1470770841072-f978cf4d019e"
    "?auto=format&fit=crop&w=1800&q=85"
)

TRIP_DETAILS_IMAGE = (
    "https://images.unsplash.com/photo-1500530855697-b586d89ba3ee"
    "?auto=format&fit=crop&w=1800&q=85"
)


# ==================================================
# CUSTOM CSS
# ==================================================

st.markdown("""
<style>

.stApp {
    background-color: #0b1120;
    color: #f8fafc;
}

[data-testid="stSidebar"] {
    background-color: #111827;
}

h1, h2, h3, h4 {
    color: #f8fafc;
}

p, label {
    color: #cbd5e1;
}

.stButton button {
    background-color: #2563eb;
    color: white;
    border-radius: 8px;
    border: none;
    padding: 8px 18px;
}

.stButton button:hover {
    background-color: #1d4ed8;
    color: white;
}

.stTextInput input,
.stNumberInput input,
.stDateInput input,
.stTextArea textarea {
    background-color: #1e293b;
    color: white;
    border-radius: 8px;
}

[data-testid="stMetric"] {
    background-color: #172554;
    padding: 18px;
    border-radius: 12px;
    border: 1px solid #263b69;
}

[data-testid="stMetricLabel"] {
    color: #bfdbfe;
}

[data-testid="stMetricValue"] {
    color: white;
}

.hero {
    background-size: cover;
    background-position: center;
    background-repeat: no-repeat;
    height: 260px;
    border-radius: 16px;
    display: flex;
    flex-direction: column;
    justify-content: center;
    padding: 35px;
    margin-bottom: 28px;
}

.hero h1 {
    color: white;
    font-size: 40px;
    font-weight: bold;
    margin-bottom: 10px;
}

.hero p {
    color: white;
    font-size: 17px;
    max-width: 650px;
}

.trip-card {
    background-color: #172554;
    padding: 20px;
    border-radius: 12px;
    margin-bottom: 15px;
    border: 1px solid #263b69;
}

hr {
    border-color: #263b69;
}

</style>
""", unsafe_allow_html=True)


# ==================================================
# HELPER FUNCTIONS
# ==================================================

def get_value(item, key, default=None):
    try:
        return item[key]
    except (KeyError, TypeError, IndexError):
        return default


def money(value):
    try:
        return f"₹{float(value):,.2f}"
    except (TypeError, ValueError):
        return "₹0.00"


def parse_date(value):
    if isinstance(value, date):
        return value

    if value:
        try:
            return date.fromisoformat(str(value)[:10])
        except ValueError:
            return date.today()

    return date.today()


def show_banner(image_url, heading, description):
    st.markdown(
        f"""
        <div class="hero"
             style="
                background-image:
                linear-gradient(
                    rgba(5,15,35,0.35),
                    rgba(5,15,35,0.70)
                ),
                url('{image_url}');
             ">
            <h1>{heading}</h1>
            <p>{description}</p>
        </div>
        """,
        unsafe_allow_html=True
    )


# ==================================================
# NAVIGATION CALLBACKS
# ==================================================

def navigate_to(page_name):
    st.session_state["page_radio"] = page_name


def open_trip(trip_id):
    st.session_state["selected_trip"] = trip_id
    st.session_state["page_radio"] = "Trip Details"


# ==================================================
# MAP FUNCTIONS
# ==================================================

@st.cache_data(ttl=86400, show_spinner=False)
def get_coordinates(destination):

    try:
        geolocator = Nominatim(
            user_agent="streamlit_trip_planner"
        )

        location = geolocator.geocode(
            destination,
            timeout=10
        )

        if location:
            return (
                location.latitude,
                location.longitude
            )

        return None

    except Exception:
        return None


@st.cache_data(ttl=1800, show_spinner=False)
def get_driving_route(
    start_lat,
    start_lon,
    end_lat,
    end_lon
):

    url = (
        "https://router.project-osrm.org/route/v1/driving/"
        f"{start_lon},{start_lat};{end_lon},{end_lat}"
    )

    params = {
        "overview": "full",
        "geometries": "geojson",
        "steps": "false"
    }

    try:
        response = requests.get(
            url,
            params=params,
            timeout=25
        )

        response.raise_for_status()

        data = response.json()

        if data.get("code") != "Ok":
            return None

        route = data["routes"][0]

        return {
            "distance_km": route["distance"] / 1000,
            "duration_minutes": route["duration"] / 60,
            "geometry": route["geometry"]["coordinates"]
        }

    except (
        requests.RequestException,
        KeyError,
        IndexError,
        ValueError
    ):
        return None


def format_duration(minutes):

    minutes = int(round(minutes))

    hours = minutes // 60
    remaining_minutes = minutes % 60

    if hours > 0:
        return f"{hours} hr {remaining_minutes} min"

    return f"{remaining_minutes} min"


def calculate_distance(lat1, lon1, lat2, lon2):

    radius = 6371

    lat1 = math.radians(lat1)
    lat2 = math.radians(lat2)

    difference_lat = math.radians(lat2 - lat1)
    difference_lon = math.radians(lon2 - lon1)

    a = (
        math.sin(difference_lat / 2) ** 2
        + math.cos(lat1)
        * math.cos(lat2)
        * math.sin(difference_lon / 2) ** 2
    )

    c = 2 * math.atan2(
        math.sqrt(a),
        math.sqrt(1 - a)
    )

    return radius * c


def create_destination_map(
    destination,
    destination_coordinates,
    current_location,
    show_route=False
):

    destination_lat, destination_lon = (
        destination_coordinates
    )

    if current_location:

        map_center = [
            current_location["latitude"],
            current_location["longitude"]
        ]

    else:

        map_center = [
            destination_lat,
            destination_lon
        ]

    trip_map = folium.Map(
        location=map_center,
        zoom_start=6,
        tiles="OpenStreetMap"
    )

    # Current location marker

    if current_location:

        folium.Marker(
            location=[
                current_location["latitude"],
                current_location["longitude"]
            ],
            tooltip="Your Current Location",
            popup="You are here",
            icon=folium.Icon(
                color="green",
                icon="home",
                prefix="fa"
            )
        ).add_to(trip_map)

    # Destination marker

    folium.Marker(
        location=[
            destination_lat,
            destination_lon
        ],
        tooltip=destination,
        popup=f"Selected destination: {destination}",
        icon=folium.Icon(
            color="red",
            icon="flag",
            prefix="fa"
        )
    ).add_to(trip_map)

    # Draw driving route when requested

    if current_location and show_route:

        route = get_driving_route(
            current_location["latitude"],
            current_location["longitude"],
            destination_lat,
            destination_lon
        )

        if route:

            route_points = [
                [point[1], point[0]]
                for point in route["geometry"]
            ]

            folium.PolyLine(
                route_points,
                color="#2563eb",
                weight=5,
                opacity=0.85,
                tooltip="Driving Route"
            ).add_to(trip_map)

            trip_map.fit_bounds([
                [
                    current_location["latitude"],
                    current_location["longitude"]
                ],
                [
                    destination_lat,
                    destination_lon
                ]
            ])

    elif current_location:

        trip_map.fit_bounds([
            [
                current_location["latitude"],
                current_location["longitude"]
            ],
            [
                destination_lat,
                destination_lon
            ]
        ])

    return trip_map


# ==================================================
# SIDEBAR NAVIGATION
# ==================================================

st.sidebar.markdown(
    """
    <h1 style="text-align:center;">
        ✈️ Trip Planner
    </h1>

    <p style="text-align:center;">
        Plan your next adventure!
    </p>
    """,
    unsafe_allow_html=True
)

page = st.sidebar.radio(
    "Navigation",
    [
        "Dashboard",
        "Create a New Trip",
        "My Trips",
        "Trip Details"
    ],
    key="page_radio"
)

st.sidebar.markdown("---")
st.sidebar.caption("Travel more. Worry less. ✨")


# ==================================================
# DASHBOARD
# ==================================================

if page == "Dashboard":

    show_banner(
        DASHBOARD_IMAGE,
        "The World Is Waiting For You",
        "Discover beautiful places, organise your itinerary "
        "and manage your travel expenses in one place."
    )

    st.title("📊 Your Travel Dashboard")

    trips = db.get_all_trips()

    total_trips = len(trips)

    total_budget = sum(
        float(get_value(trip, "budget", 0) or 0)
        for trip in trips
    )

    total_spent = 0

    for trip in trips:

        trip_id = get_value(trip, "id")

        expenses = db.get_expenses(trip_id)

        total_spent += sum(
            float(
                get_value(expense, "amount", 0) or 0
            )
            for expense in expenses
        )

    remaining_budget = total_budget - total_spent

    st.markdown("### Your Travel Overview")

    col1, col2, col3, col4 = st.columns(4)

    col1.metric("Total Trips", total_trips)
    col2.metric("Total Budget", money(total_budget))
    col3.metric("Total Spent", money(total_spent))
    col4.metric("Remaining Budget", money(remaining_budget))

    st.markdown("---")

    # Create trip section

    col1, col2 = st.columns(2)

    with col1:

        st.subheader("🧳 Create a New Trip")

        st.write(
            "Plan your next getaway! Add your trip details "
            "and start exploring."
        )

        st.button(
            "➕ Create Trip",
            use_container_width=True,
            on_click=navigate_to,
            args=("Create a New Trip",)
        )

    with col2:

        st.subheader("📍 Your Recent Trips")

        if trips:

            for trip in trips[:3]:

                name = get_value(
                    trip, "name", "Untitled Trip"
                )

                destination = get_value(
                    trip, "destination", "Unknown"
                )

                st.markdown(
                    f"""
                    <div class="trip-card">
                        <h4>{name}</h4>
                        <p>📍 {destination}</p>
                    </div>
                    """,
                    unsafe_allow_html=True
                )

        else:

            st.info("No trips created yet.")

    st.markdown("---")

    st.subheader("Explore Your Journey")

    st.write(
        "View your trip details, itinerary and manage "
        "your travel expenses."
    )

    st.button(
        "View Trip Details",
        on_click=navigate_to,
        args=("Trip Details",)
    )


# ==================================================
# CREATE A NEW TRIP
# ==================================================

elif page == "Create a New Trip":

    st.title("🌍 Create a New Trip")

    st.write("Enter your travel details below.")

    col1, col2 = st.columns([1, 1.5])

    with col1:

        st.image(
            CREATE_TRIP_IMAGE,
            use_container_width=True
        )

    with col2:

        st.markdown(
            "### Your Next Adventure Starts Here"
        )

        st.write(
            "Choose your destination, set your travel dates "
            "and prepare for an unforgettable journey."
        )

        st.write("✈️ Plan your journey")
        st.write("📅 Organise your dates")
        st.write("💰 Manage your budget")

    st.markdown("---")

    with st.form("create_trip_form"):

        st.subheader("Trip Information")

        trip_name = st.text_input(
            "Trip Name",
            placeholder="Example: Summer Vacation"
        )

        destination = st.text_input(
            "Destination",
            placeholder="Example: Goa, India"
        )

        col1, col2 = st.columns(2)

        with col1:

            start_date = st.date_input(
                "Start Date",
                value=date.today()
            )

        with col2:

            end_date = st.date_input(
                "End Date",
                value=date.today() + timedelta(days=3)
            )

        budget = st.number_input(
            "Total Budget (₹)",
            min_value=1.0,
            value=10000.0,
            step=500.0
        )

        description = st.text_area(
            "Trip Description",
            placeholder="Write something about your trip..."
        )

        submit = st.form_submit_button(
            "Create Trip",
            use_container_width=True
        )

        if submit:

            if not trip_name.strip():

                st.error("Please enter a trip name.")

            elif not destination.strip():

                st.error("Please enter a destination.")

            elif end_date < start_date:

                st.error(
                    "End date cannot be before start date."
                )

            else:

                db.add_trip(
                    trip_name,
                    destination,
                    start_date.isoformat(),
                    end_date.isoformat(),
                    budget,
                    description
                )

                st.success(
                    "Your trip has been created successfully!"
                )

                st.rerun()


# ==================================================
# MY TRIPS
# ==================================================

elif page == "My Trips":

    show_banner(
        MY_TRIPS_IMAGE,
        "Your Adventures",
        "All your planned journeys in one place. "
        "Explore, manage and organise your trips."
    )

    st.title("🧳 My Trips")

    trips = db.get_all_trips()

    if not trips:

        st.info(
            "No trips available. Create your first trip!"
        )

    else:

        search = st.text_input(
            "🔍 Search trips by name or destination"
        )

        filtered_trips = []

        for trip in trips:

            name = str(
                get_value(trip, "name", "")
            )

            destination = str(
                get_value(trip, "destination", "")
            )

            if (
                search.lower() in name.lower()
                or search.lower() in destination.lower()
            ):

                filtered_trips.append(trip)

        if not filtered_trips:

            st.warning("No matching trips found.")

        for trip in filtered_trips:

            trip_id = get_value(trip, "id")

            name = get_value(
                trip, "name", "Untitled Trip"
            )

            destination = get_value(
                trip, "destination", "Unknown"
            )

            start = get_value(
                trip, "start_date", ""
            )

            end = get_value(
                trip, "end_date", ""
            )

            budget = get_value(
                trip, "budget", 0
            )

            description = get_value(
                trip, "description", ""
            )

            st.markdown(
                f"""
                <div class="trip-card">
                    <h3>📍 {name}</h3>
                    <p><b>Destination:</b> {destination}</p>
                    <p><b>Start Date:</b> {start}</p>
                    <p><b>End Date:</b> {end}</p>
                    <p><b>Budget:</b> {money(budget)}</p>
                    <p>{description}</p>
                </div>
                """,
                unsafe_allow_html=True
            )

            col1, col2 = st.columns(2)

            with col1:

                st.button(
                    "View Trip Details",
                    key=f"view_{trip_id}",
                    on_click=open_trip,
                    args=(trip_id,)
                )

            with col2:

                if st.button(
                    "Delete Trip",
                    key=f"delete_{trip_id}"
                ):

                    st.session_state[
                        f"confirm_delete_{trip_id}"
                    ] = True

            if st.session_state.get(
                f"confirm_delete_{trip_id}",
                False
            ):

                st.warning(
                    f"Are you sure you want to delete {name}?"
                )

                yes_col, no_col = st.columns(2)

                with yes_col:

                    if st.button(
                        "Yes, Delete",
                        key=f"yes_{trip_id}"
                    ):

                        db.delete_trip(trip_id)

                        st.session_state[
                            f"confirm_delete_{trip_id}"
                        ] = False

                        st.success("Trip deleted.")

                        st.rerun()

                with no_col:

                    if st.button(
                        "Cancel",
                        key=f"no_{trip_id}"
                    ):

                        st.session_state[
                            f"confirm_delete_{trip_id}"
                        ] = False

                        st.rerun()


# ==================================================
# TRIP DETAILS
# ==================================================

elif page == "Trip Details":

    show_banner(
        TRIP_DETAILS_IMAGE,
        "Explore Your Journey",
        "View your trip details, organise activities "
        "and manage your travel expenses."
    )

    st.title("📋 Trip Details")

    trips = db.get_all_trips()

    if not trips:

        st.info(
            "Create a trip first to view its details."
        )

    else:

        trip_options = {}

        for trip in trips:

            trip_id = get_value(
                trip, "id"
            )

            trip_name = get_value(
                trip, "name", "Untitled Trip"
            )

            trip_options[
                f"{trip_name} (ID: {trip_id})"
            ] = trip_id

        option_names = list(
            trip_options.keys()
        )

        selected_trip_id = st.session_state.get(
            "selected_trip"
        )

        default_index = 0

        if selected_trip_id in trip_options.values():

            default_index = list(
                trip_options.values()
            ).index(selected_trip_id)

        selected_name = st.selectbox(
            "Select a Trip",
            option_names,
            index=default_index
        )

        selected_trip_id = trip_options[
            selected_name
        ]

        trip = db.get_trip(selected_trip_id)

        if trip:

            name = get_value(
                trip, "name", ""
            )

            destination = get_value(
                trip, "destination", ""
            )

            start = get_value(
                trip, "start_date", ""
            )

            end = get_value(
                trip, "end_date", ""
            )

            budget = float(
                get_value(trip, "budget", 0) or 0
            )

            description = get_value(
                trip, "description", ""
            )

            st.markdown(
                f"""
                <div class="trip-card">
                    <h2>📍 {name}</h2>
                    <p><b>Destination:</b> {destination}</p>
                    <p><b>Start Date:</b> {start}</p>
                    <p><b>End Date:</b> {end}</p>
                    <p><b>Budget:</b> {money(budget)}</p>
                    <p>{description}</p>
                </div>
                """,
                unsafe_allow_html=True
            )

            # ==========================================
            # INTERACTIVE MAP - NOW IN TRIP DETAILS
            # ==========================================

            st.markdown("---")

            st.subheader("🗺️ Destination Map")

            st.write(
                "Find your destination on the map and calculate "
                "the driving distance and estimated travel time "
                "from your current location."
            )

            # Get browser location

            location_result = streamlit_geolocation()

            if (
                isinstance(location_result, dict)
                and location_result.get("latitude") is not None
                and location_result.get("longitude") is not None
            ):

                st.session_state["current_location"] = {
                    "latitude": float(
                        location_result["latitude"]
                    ),
                    "longitude": float(
                        location_result["longitude"]
                    )
                }

            current_location = st.session_state.get(
                "current_location"
            )

            if current_location:

                st.success(
                    "Your current location has been detected."
                )

            else:

                st.info(
                    "Allow your browser to access your location "
                    "to calculate your route."
                )

            # Find destination coordinates

            with st.spinner(
                "Finding destination on the map..."
            ):

                destination_coordinates = get_coordinates(
                    destination
                )

            if destination_coordinates is None:

                st.warning(
                    "We could not find this destination. "
                    "Please check the destination name. "
                    "For better results, include the city and country, "
                    "for example: Munnar, Kerala, India."
                )

            else:

                # Each trip has its own route-selection state.

                route_state_key = (
                    f"route_selected_{selected_trip_id}"
                )

                show_route = st.session_state.get(
                    route_state_key,
                    False
                )

                destination_map = create_destination_map(
                    destination,
                    destination_coordinates,
                    current_location,
                    show_route
                )

                st.write(
                    "Click the red destination marker on the map "
                    "to display the driving route."
                )

                map_result = st_folium(
                    destination_map,
                    width=None,
                    height=450,
                    returned_objects=[
                        "last_object_clicked"
                    ],
                    key=f"trip_map_{selected_trip_id}"
                )

                # Detect a click close to the destination marker.

                if map_result:

                    clicked = map_result.get(
                        "last_object_clicked"
                    )

                    if clicked:

                        clicked_lat = clicked.get("lat")
                        clicked_lon = clicked.get("lng")

                        if (
                            clicked_lat is not None
                            and clicked_lon is not None
                        ):

                            distance_from_marker = calculate_distance(
                                clicked_lat,
                                clicked_lon,
                                destination_coordinates[0],
                                destination_coordinates[1]
                            )

                            if (
                                distance_from_marker <= 2
                                and not show_route
                            ):

                                st.session_state[
                                    route_state_key
                                ] = True

                                st.rerun()

                # Display route information

                if current_location and show_route:

                    with st.spinner(
                        "Calculating driving distance and time..."
                    ):

                        route = get_driving_route(
                            current_location["latitude"],
                            current_location["longitude"],
                            destination_coordinates[0],
                            destination_coordinates[1]
                        )

                    if route:

                        st.markdown("### 🚗 Your Route Information")

                        col1, col2 = st.columns(2)

                        col1.metric(
                            "Driving Distance",
                            f"{route['distance_km']:,.1f} km"
                        )

                        col2.metric(
                            "Estimated Driving Time",
                            format_duration(
                                route["duration_minutes"]
                            )
                        )

                        st.caption(
                            "This is an estimated driving time, "
                            "not a live traffic prediction. Actual "
                            "travel time may vary."
                        )

                    else:

                        st.warning(
                            "Unable to calculate the driving route. "
                            "Please try again later."
                        )

                elif not current_location:

                    st.info(
                        "Your destination is displayed on the map. "
                        "Allow location access to calculate distance "
                        "and travel time."
                    )

                if show_route:

                    if st.button(
                        "Clear Route",
                        key=f"clear_route_{selected_trip_id}"
                    ):

                        st.session_state[
                            route_state_key
                        ] = False

                        st.rerun()

            # ==========================================
            # EDIT TRIP
            # ==========================================

            st.markdown("---")

            with st.expander("✏️ Edit Trip Details"):

                with st.form("edit_trip_form"):

                    new_name = st.text_input(
                        "Trip Name",
                        value=name
                    )

                    new_destination = st.text_input(
                        "Destination",
                        value=destination
                    )

                    col1, col2 = st.columns(2)

                    with col1:

                        new_start = st.date_input(
                            "Start Date",
                            value=parse_date(start),
                            key="edit_start"
                        )

                    with col2:

                        new_end = st.date_input(
                            "End Date",
                            value=parse_date(end),
                            key="edit_end"
                        )

                    new_budget = st.number_input(
                        "Budget (₹)",
                        min_value=1.0,
                        value=max(budget, 1.0)
                    )

                    new_description = st.text_area(
                        "Description",
                        value=description
                    )

                    update = st.form_submit_button(
                        "Update Trip"
                    )

                    if update:

                        if not new_name.strip():

                            st.error(
                                "Trip name is required."
                            )

                        elif not new_destination.strip():

                            st.error(
                                "Destination is required."
                            )

                        elif new_end < new_start:

                            st.error(
                                "End date cannot be before start date."
                            )

                        else:

                            db.update_trip(
                                selected_trip_id,
                                new_name,
                                new_destination,
                                new_start.isoformat(),
                                new_end.isoformat(),
                                new_budget,
                                new_description
                            )

                            st.success(
                                "Trip updated successfully!"
                            )

                            st.rerun()

            # ==========================================
            # ITINERARY
            # ==========================================

            st.markdown("---")

            st.subheader("🗓️ Travel Itinerary")

            itinerary = db.get_itinerary(
                selected_trip_id
            )

            if itinerary:

                for item in itinerary:

                    item_id = get_value(
                        item, "id"
                    )

                    visit_date = get_value(
                        item, "visit_date", ""
                    )

                    place = get_value(
                        item, "place", ""
                    )

                    activity = get_value(
                        item, "activity", ""
                    )

                    notes = get_value(
                        item, "notes", ""
                    )

                    st.markdown(
                        f"""
                        <div class="trip-card">
                            <h4>📍 {place}</h4>
                            <p><b>Date:</b> {visit_date}</p>
                            <p><b>Activity:</b> {activity}</p>
                            <p><b>Notes:</b> {notes}</p>
                        </div>
                        """,
                        unsafe_allow_html=True
                    )

                    if st.button(
                        "Delete Activity",
                        key=f"delete_activity_{item_id}"
                    ):

                        db.delete_itinerary(item_id)

                        st.rerun()

            else:

                st.info(
                    "No itinerary activities added yet."
                )

            with st.expander(
                "➕ Add Itinerary Activity"
            ):

                with st.form("add_itinerary_form"):

                    visit_date = st.date_input(
                        "Visit Date",
                        value=date.today()
                    )

                    place = st.text_input(
                        "Place to Visit"
                    )

                    activity = st.text_input(
                        "Activity"
                    )

                    notes = st.text_area(
                        "Notes"
                    )

                    add_activity = st.form_submit_button(
                        "Add Activity"
                    )

                    if add_activity:

                        if not place.strip():

                            st.error(
                                "Please enter a place."
                            )

                        elif not activity.strip():

                            st.error(
                                "Please enter an activity."
                            )

                        else:

                            db.add_itinerary(
                                selected_trip_id,
                                visit_date.isoformat(),
                                place,
                                activity,
                                notes
                            )

                            st.success("Activity added!")

                            st.rerun()

            # ==========================================
            # EXPENSES
            # ==========================================

            st.markdown("---")

            st.subheader("💰 Travel Expenses")

            expenses = db.get_expenses(
                selected_trip_id
            )

            total_spent = sum(
                float(
                    get_value(
                        expense, "amount", 0
                    ) or 0
                )
                for expense in expenses
            )

            remaining = budget - total_spent

            col1, col2, col3 = st.columns(3)

            col1.metric(
                "Total Budget",
                money(budget)
            )

            col2.metric(
                "Total Spent",
                money(total_spent)
            )

            col3.metric(
                "Remaining Budget",
                money(remaining)
            )

            if budget > 0:

                st.write("Budget Usage")

                st.progress(
                    min(total_spent / budget, 1.0)
                )

            if total_spent > budget:

                st.warning(
                    "You have exceeded your trip budget!"
                )

            if expenses:

                expense_data = []

                for expense in expenses:

                    expense_data.append({

                        "Date": get_value(
                            expense,
                            "expense_date",
                            ""
                        ),

                        "Category": get_value(
                            expense,
                            "category",
                            ""
                        ),

                        "Amount": float(
                            get_value(
                                expense,
                                "amount",
                                0
                            ) or 0
                        ),

                        "Description": get_value(
                            expense,
                            "description",
                            ""
                        )
                    })

                expense_df = pd.DataFrame(
                    expense_data
                )

                st.dataframe(
                    expense_df,
                    use_container_width=True,
                    hide_index=True
                )

                category_totals = expense_df.groupby(
                    "Category"
                )["Amount"].sum().reset_index()

                fig = px.pie(
                    category_totals,
                    names="Category",
                    values="Amount",
                    title="Expenses by Category",
                    hole=0.4
                )

                fig.update_layout(
                    paper_bgcolor="#0b1120",
                    plot_bgcolor="#0b1120",
                    font_color="white"
                )

                st.plotly_chart(
                    fig,
                    use_container_width=True
                )

                st.markdown("### Delete an Expense")

                expense_labels = {}

                for expense in expenses:

                    expense_id = get_value(
                        expense, "id"
                    )

                    label = (
                        f"{get_value(expense, 'category', 'Expense')} - "
                        f"{money(get_value(expense, 'amount', 0))} - "
                        f"{get_value(expense, 'expense_date', '')}"
                    )

                    expense_labels[label] = expense_id

                selected_expense = st.selectbox(
                    "Choose an expense",
                    list(expense_labels.keys())
                )

                if st.button(
                    "Delete Selected Expense"
                ):

                    db.delete_expense(
                        expense_labels[selected_expense]
                    )

                    st.success("Expense deleted.")

                    st.rerun()

            else:

                st.info("No expenses added yet.")

            # ==========================================
            # ADD EXPENSE
            # ==========================================

            with st.expander(
                "➕ Add New Expense"
            ):

                with st.form("add_expense_form"):

                    expense_date = st.date_input(
                        "Expense Date",
                        value=date.today()
                    )

                    category = st.selectbox(
                        "Expense Category",
                        [
                            "Food",
                            "Transport",
                            "Accommodation",
                            "Shopping",
                            "Activities",
                            "Other"
                        ]
                    )

                    amount = st.number_input(
                        "Amount (₹)",
                        min_value=1.0,
                        value=100.0,
                        step=50.0
                    )

                    expense_description = st.text_input(
                        "Description",
                        placeholder="Example: Lunch, hotel, taxi..."
                    )

                    add_expense = st.form_submit_button(
                        "Add Expense"
                    )

                    if add_expense:

                        db.add_expense(
                            selected_trip_id,
                            expense_date.isoformat(),
                            category,
                            amount,
                            expense_description
                        )

                        st.success(
                            "Expense added successfully!"
                        )

                        st.rerun()

        else:

            st.error(
                "Unable to find the selected trip."
            )


# ==================================================
# FOOTER
# ==================================================

st.markdown("---")

st.markdown(
    """
    <div style="
        text-align:center;
        color:#94a3b8;
        padding:15px;
    ">
        ✈️ Trip Planner |
        Plan your journey, enjoy your adventure. ❤️
    </div>
    """,
    unsafe_allow_html=True
)
