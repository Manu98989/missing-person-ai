import os
import uuid
import json
import tempfile

import streamlit as st

from pages.helper import db_queries
from pages.helper.data_models import PublicSubmissions
from pages.helper.utils import (
    image_obj_to_numpy,
    extract_face_mesh_landmarks,
    extract_unique_faces_from_video,
)

st.set_page_config("Public Submission", initial_sidebar_state="collapsed")

st.title("Report a Sighting")

upload_mode = st.radio(
    "Upload type",
    options=["Image", "Video"],
    horizontal=True,
)

image_col, form_col = st.columns(2)

save_flag = 0
extracted_faces = []
face_mesh = None
face_detected = False
unique_id = None
uploaded_file_path = None

# ───────────────────────────────────────── IMAGE ───────────────────────────────
if upload_mode == "Image":
    with image_col:
        image_obj = st.file_uploader(
            "Upload photo", type=["jpg", "jpeg", "png"], key="user_submission_img"
        )

        if image_obj:
            unique_id = str(uuid.uuid4())

            with st.spinner("Processing..."):
                os.makedirs("./resources", exist_ok=True)

                uploaded_file_path = "./resources/" + unique_id + ".jpg"

                # save image
                image_bytes = image_obj.read()
                with open(uploaded_file_path, "wb") as f:
                    f.write(image_bytes)

            # display image
            image_obj.seek(0)
            st.image(image_obj, width=200)
            image_obj.seek(0)

            # face detection
            image_numpy = image_obj_to_numpy(image_obj)
            face_mesh = extract_face_mesh_landmarks(image_numpy)

            if face_mesh is None:
                if os.path.exists(uploaded_file_path):
                    os.remove(uploaded_file_path)
                face_detected = False
                st.error("❌ No face detected. Try another image.")
            else:
                face_detected = True
                st.success("✅ Face detected.")

    # ── Form (Image) ───────────────────────────────────────────────────────────
    if image_obj and face_detected:
        with form_col.form(key="image_submission_form"):
            sub_name = st.text_input("Your Name *")
            mobile_number = st.text_input("Your Mobile Number * (10 digits)")
            email = st.text_input("Your Email")
            address = st.text_input("Location where person was seen *")
            birth_marks = st.text_input("Birth Marks / Identifying Features")

            submit_bt = st.form_submit_button("Submit")

            if submit_bt:
                errors = []

                if not sub_name.strip():
                    errors.append("❌ Name required")
                if not mobile_number.strip():
                    errors.append("❌ Mobile required")
                elif not mobile_number.isdigit() or len(mobile_number) != 10:
                    errors.append("❌ Invalid mobile number")
                if not address.strip():
                    errors.append("❌ Location required")

                if errors:
                    for e in errors:
                        st.error(e)
                else:
                    details = PublicSubmissions(
                        submitted_by=sub_name.strip(),
                        location=address.strip(),
                        email=email.strip() or None,
                        face_mesh=json.dumps(face_mesh),
                        id=unique_id,
                        mobile=mobile_number.strip(),
                        birth_marks=birth_marks.strip() or None,
                        status="NF",
                    )

                    db_queries.new_public_case(details)
                    save_flag = 1

        if save_flag == 1:
            st.success("✅ Submission received successfully!")

# ───────────────────────────────────────── VIDEO ───────────────────────────────
else:
    with image_col:
        video_obj = st.file_uploader(
            "Upload video", type=["mp4", "mov", "avi"], key="user_submission_video"
        )

        if video_obj:
            with st.spinner("Extracting faces..."):
                suffix = "." + video_obj.name.rsplit(".", 1)[-1]

                with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
                    tmp.write(video_obj.read())
                    tmp_path = tmp.name

                extracted_faces = extract_unique_faces_from_video(tmp_path)
                os.unlink(tmp_path)

                if not extracted_faces:
                    st.error("❌ No faces detected in video.")
                else:
                    st.success(f"✅ {len(extracted_faces)} face(s) found")

                    cols = st.columns(min(len(extracted_faces), 4))
                    for i, (_, frame) in enumerate(extracted_faces):
                        cols[i % 4].image(frame, width=100)

    # ── Form (Video) ───────────────────────────────────────────────────────────
    if extracted_faces:
        with form_col.form(key="video_submission_form"):
            sub_name = st.text_input("Your Name *")
            mobile_number = st.text_input("Your Mobile Number * (10 digits)")
            email = st.text_input("Your Email")
            address = st.text_input("Location where person was seen *")
            birth_marks = st.text_input("Birth Marks / Identifying Features")

            submit_bt = st.form_submit_button(
                f"Submit {len(extracted_faces)} face(s)"
            )

            if submit_bt:
                errors = []

                if not sub_name.strip():
                    errors.append("❌ Name required")
                if not mobile_number.strip():
                    errors.append("❌ Mobile required")
                elif not mobile_number.isdigit() or len(mobile_number) != 10:
                    errors.append("❌ Invalid mobile number")
                if not address.strip():
                    errors.append("❌ Location required")

                if errors:
                    for e in errors:
                        st.error(e)
                else:
                    count = 0

                    for landmarks, _ in extracted_faces:
                        sub_id = str(uuid.uuid4())

                        details = PublicSubmissions(
                            submitted_by=sub_name.strip(),
                            location=address.strip(),
                            email=email.strip() or None,
                            face_mesh=json.dumps(landmarks),
                            id=sub_id,
                            mobile=mobile_number.strip(),
                            birth_marks=birth_marks.strip() or None,
                            status="NF",
                        )

                        db_queries.new_public_case(details)
                        count += 1

                    st.success(f"✅ {count} submission(s) saved successfully!")