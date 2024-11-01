from flask import Flask, render_template,request,session,redirect,flash,url_for,jsonify
from config import Database
from datetime import datetime
import random
import os

app = Flask(__name__)

app.secret_key = 'your_secret_key'
# Initialize Database
db = Database()

#Guest Block

@app.route("/")
def home():
    return render_template("guest/index.html")

@app.route("/index")
def index():
    return render_template("guest/index.html")

@app.route("/logout")
def logout():
    # Clear the session data
    session.clear()
    flash("You have been logged out.", "info")
    return redirect(url_for('login'))

@app.route("/login", methods=["GET", "POST"])
def login():
    user_status =None
    if request.method == "POST":
        username = request.form['username']
        password = request.form['password']

        # Fetch user from the database
        query = f"SELECT * FROM tbl_login WHERE username = '{username}' and password='{password}'"
        user = db.fetchone(query)

        if user:
            session['user_id'] = user['id']
            # Verify the password
            if user['type']=='admin':
                flash("Login successful!", "success")
                return redirect(url_for('adminhome'))  
            elif user['type']=='land_owner':
                status_query = f"SELECT status FROM tbl_land_owner WHERE login_id={user['id']}"
                status = db.fetchone(status_query)
                print(f"status:{status}")
                if status['status'] == 1:
                    flash("Login successful!", "success")
                    return redirect(url_for('landownerhome'))
                elif status['status'] == 2:
                    user_status= 'rejected by admin'
                else:
                    user_status= 'pending'

            elif user['type']=='mate':
                flash("Login successful!", "success")
                return redirect(url_for('matehome'))
            else:
                flash("Invalid username or password.", "danger")
                user_status= 'invalid'
        else:
            flash("User not found.", "danger")
        print(f"user status:{user_status}")
    return render_template("guest/login.html", user_status=user_status)

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        # Fetch data from the form
        name = request.form.get('name')
        ward_id = request.form.get('ward_id')
        panchayat_id = request.form.get('panchayat_id')
        phone = request.form.get('phone')
        address = request.form.get('address')
        username = request.form.get('username')
        password = request.form.get('password')
        
     

        try:
            # Insert into tbl_login first
            insert_login_query = f"""
            INSERT INTO tbl_login (username, password, type)
            VALUES ('{username}', '{password}', 'land_owner')
            """
            login_id = db.executeAndReturnId(insert_login_query)  # Assuming this returns the inserted login_id

            # Insert into tbl_land_owner with the returned login_id
            insert_land_owner_query = f"""
            INSERT INTO tbl_land_owner (name, ward_id, panchayath_id, phone, address, login_id)
            VALUES ('{name}', {ward_id}, {panchayat_id}, '{phone}', '{address}', {login_id})
            """
            db.single_insert(insert_land_owner_query)
            
            flash("Land owner registered successfully!", "success")
        except Exception as e:
            flash(f"Failed to register land owner: {str(e)}", "danger")
        
        return redirect(url_for('login'))

    # Fetch Panchayats and Wards to populate the dropdowns in the form
    panchayats = db.fetchall("SELECT id, panchayat_name FROM tbl_panchayat")
    wards = db.fetchall("SELECT id, ward_name FROM tbl_ward")
    
    return render_template("guest/register.html", panchayats=panchayats, wards=wards)


@app.route("/get-wards/<int:panchayat_id>", methods=["GET"])
def get_wards(panchayat_id):
    try:
        # Fetch wards associated with the selected panchayat
        wards = db.fetchall(f"SELECT id, ward_name FROM tbl_ward WHERE panchayat_id = {panchayat_id}")
        return jsonify(wards)
    except Exception as e:
        return jsonify({"error": str(e)})




#admin Block

@app.route("/admin-home")
def adminhome():
    # Query for total workers, attendance records, mates, and works
    total_workers = db.fetchone("SELECT COUNT(*) as count FROM tbl_workers")['count']
    total_attendance_records = db.fetchone("SELECT COUNT(*) as count FROM tbl_attendance")['count']
    total_mates = db.fetchone("SELECT COUNT(*) as count FROM tbl_mate")['count']
    total_works = db.fetchone("SELECT COUNT(*) as count FROM tbl_work")['count']
    total_land_works = db.fetchone("SELECT COUNT(*) as count FROM tbl_land_work")['count']
    total_land_owners = db.fetchone("SELECT COUNT(*) as count FROM tbl_land_owner")['count']
    total_open_works = db.fetchone("SELECT COUNT(*) as count FROM tbl_work where status<>2")['count']
    total_closed_works = db.fetchone("SELECT COUNT(*) as count FROM tbl_work where status=2")['count']

    # Monthly attendance count
    attendance_by_month = db.fetchall("""
        SELECT MONTH(date) as month, COUNT(*) as count 
        FROM tbl_attendance 
        GROUP BY MONTH(date)
        ORDER BY MONTH(date)
    """)

    # Work distribution by type
    work_distribution = db.fetchall("""
        SELECT work_category_id, COUNT(*) as count 
        FROM tbl_work 
        GROUP BY work_category_id
    """)

    return render_template(
        "admin/index.html", 
        total_workers=total_workers, 
        total_attendance_records=total_attendance_records,
        total_mates=total_mates, 
        total_works=total_works,
        attendance_by_month=attendance_by_month, 
        work_distribution=work_distribution,
        total_land_works=total_land_works,
        total_land_owners=total_land_owners,
        total_open_works=total_open_works,
        total_closed_works=total_closed_works
    )


@app.route("/admin-panchayat", methods=["GET", "POST"])
def admin_panchayat():
    if request.method == "POST":
        panchayat_name = request.form['panchayat']  # Get the Panchayat name from the form
        panchayat_id = request.form.get('panchayat_id')  # Hidden field for the Panchayat ID if editing

        if panchayat_id:  # Update operation
            try:
                update_panchayat_query = f"""
                UPDATE tbl_panchayat 
                SET panchayat_name = '{panchayat_name}'
                WHERE id = {panchayat_id}
                """
                db.execute(update_panchayat_query)
                flash("Panchayat updated successfully!", "success")
            except Exception as e:
                flash(f"Failed to update Panchayat: {str(e)}", "danger")
        else:  # Create operation
            try:
                insert_panchayat_query = f"""
                INSERT INTO tbl_panchayat (panchayat_name) 
                VALUES ('{panchayat_name}')
                """
                db.single_insert(insert_panchayat_query)
                flash("Panchayat added successfully!", "success")
            except Exception as e:
                flash(f"Failed to add Panchayat: {str(e)}", "danger")

        return redirect(url_for('admin_panchayat'))

    # Fetch all Panchayats to display in the table
    panchayats = db.fetchall("SELECT * FROM tbl_panchayat")

    # Check if there's an 'edit' parameter in the URL
    course_to_edit = None
    if 'edit' in request.args:
        panchayat_id = request.args.get('edit')
        course_to_edit = db.fetchone(f"SELECT * FROM tbl_panchayat WHERE id = {panchayat_id}")

    return render_template("admin/panchayat.html", panchayats=panchayats, course_to_edit=course_to_edit)

@app.route("/delete-panchayat/<int:panchayat_id>", methods=["POST"])
def delete_panchayat(panchayat_id):
    try:
        delete_panchayat_query = f"DELETE FROM tbl_panchayat WHERE id = {panchayat_id}"
        db.execute(delete_panchayat_query)
        flash("Panchayat deleted successfully!", "success")
    except Exception as e:
        flash(f"Failed to delete Panchayat: {str(e)}", "danger")

    return redirect(url_for('admin_panchayat'))

@app.route("/admin-ward", methods=["GET", "POST"])
def admin_ward():
    # Fetch all Panchayats for the dropdown
    panchayats = db.fetchall("SELECT id, panchayat_name FROM tbl_panchayat")

    if request.method == "POST":
        ward_name = request.form['ward']  # Get the Ward name from the form
        panchayat_id = request.form['panchayat_id']  # Get the Panchayat ID from the form
        ward_id = request.form.get('ward_id')  # Hidden field for the Ward ID if editing

        if ward_id:  # Update operation
            try:
                update_ward_query = f"""
                UPDATE tbl_ward 
                SET ward_name = '{ward_name}', panchayat_id = {panchayat_id}
                WHERE id = {ward_id}
                """
                db.execute(update_ward_query)
                flash("Ward updated successfully!", "success")
            except Exception as e:
                flash(f"Failed to update Ward: {str(e)}", "danger")
        else:  # Create operation
            try:
                insert_ward_query = f"""
                INSERT INTO tbl_ward (ward_name, panchayat_id) 
                VALUES ('{ward_name}', {panchayat_id})
                """
                db.single_insert(insert_ward_query)
                flash("Ward added successfully!", "success")
            except Exception as e:
                flash(f"Failed to add Ward: {str(e)}", "danger")

        return redirect(url_for('admin_ward'))

    # Fetch all Wards with their corresponding Panchayat names to display in the table
    wards = db.fetchall("""
        SELECT w.*, p.panchayat_name
        FROM tbl_ward w
        JOIN tbl_panchayat p ON w.panchayat_id = p.id
    """)

    # Check if there's an 'edit' parameter in the URL
    ward_to_edit = None
    if 'edit' in request.args:
        ward_id = request.args.get('edit')
        ward_to_edit = db.fetchone(f"SELECT * FROM tbl_ward WHERE id = {ward_id}")

    return render_template("admin/ward.html", wards=wards, ward_to_edit=ward_to_edit, panchayats=panchayats)


@app.route("/delete-ward/<int:ward_id>", methods=["POST"])
def delete_ward(ward_id):
    try:
        delete_ward_query = f"DELETE FROM tbl_ward WHERE id = {ward_id}"
        db.execute(delete_ward_query)
        flash("Ward deleted successfully!", "success")
    except Exception as e:
        flash(f"Failed to delete Ward: {str(e)}", "danger")

    return redirect(url_for('admin_ward'))

@app.route("/admin-land-category", methods=["GET", "POST"])
def admin_land_category():
    if request.method == "POST":
        land_category_name = request.form['land_category']  # Get the land category name from the form
        land_category_id = request.form.get('land_category_id')  # Hidden field for the land category ID if editing

        if land_category_id:  # Update operation
            try:
                update_land_category_query = f"""
                UPDATE tbl_land_category 
                SET land_category_name = '{land_category_name}'
                WHERE id = {land_category_id}
                """
                db.execute(update_land_category_query)
                flash("Land category updated successfully!", "success")
            except Exception as e:
                flash(f"Failed to update Land category: {str(e)}", "danger")
        else:  # Create operation
            try:
                insert_land_category_query = f"""
                INSERT INTO tbl_land_category (land_category_name) 
                VALUES ('{land_category_name}')
                """
                db.single_insert(insert_land_category_query)
                flash("Land category added successfully!", "success")
            except Exception as e:
                flash(f"Failed to add Land category: {str(e)}", "danger")

        return redirect(url_for('admin_land_category'))

    # Fetch all Land Categories to display in the table
    land_categories = db.fetchall("SELECT * FROM tbl_land_category")

    land_category_to_edit = None
    if 'edit' in request.args:
        land_category_id = request.args.get('edit')
        land_category_to_edit = db.fetchone(f"SELECT * FROM tbl_land_category WHERE id = {land_category_id}")

    return render_template("admin/land_category.html", land_categories=land_categories, land_category_to_edit=land_category_to_edit)

@app.route("/delete-land-category/<int:land_category_id>", methods=["POST"])
def delete_land_category(land_category_id):
    try:
        delete_land_category_query = f"DELETE FROM tbl_land_category WHERE id = {land_category_id}"
        db.execute(delete_land_category_query)
        flash("Land category deleted successfully!", "success")
    except Exception as e:
        flash(f"Failed to delete Land category: {str(e)}", "danger")

    return redirect(url_for('admin_land_category'))

@app.route("/admin-work-type", methods=["GET", "POST"])
def admin_work_type():
    if request.method == "POST":
        work_type_name = request.form['work_type']  # Get the work type name from the form
        work_type_details = request.form['work_type_details']  # Get work type details from the form
        work_type_id = request.form.get('work_type_id')  # Hidden field for the work type ID if editing

        if work_type_id:  # Update operation
            try:
                update_work_type_query = f"""
                UPDATE tbl_work_type 
                SET work_type_name = '{work_type_name}', work_type_details = '{work_type_details}'
                WHERE id = {work_type_id}
                """
                db.execute(update_work_type_query)
                flash("Work type updated successfully!", "success")
            except Exception as e:
                flash(f"Failed to update Work type: {str(e)}", "danger")
        else:  # Create operation
            try:
                insert_work_type_query = f"""
                INSERT INTO tbl_work_type (work_type_name, work_type_details) 
                VALUES ('{work_type_name}', '{work_type_details}')
                """
                db.single_insert(insert_work_type_query)
                flash("Work type added successfully!", "success")
            except Exception as e:
                flash(f"Failed to add Work type: {str(e)}", "danger")

        return redirect(url_for('admin_work_type'))

    # Fetch all Work Types to display in the table
    work_types = db.fetchall("SELECT * FROM tbl_work_type")

    work_type_to_edit = None
    if 'edit' in request.args:
        work_type_id = request.args.get('edit')
        work_type_to_edit = db.fetchone(f"SELECT * FROM tbl_work_type WHERE id = {work_type_id}")

    return render_template("admin/work_type.html", work_types=work_types, work_type_to_edit=work_type_to_edit)

@app.route("/delete-work-type/<int:work_type_id>", methods=["POST"])
def delete_work_type(work_type_id):
    try:
        delete_work_type_query = f"DELETE FROM tbl_work_type WHERE id = {work_type_id}"
        db.execute(delete_work_type_query)
        flash("Work type deleted successfully!", "success")
    except Exception as e:
        flash(f"Failed to delete Work type: {str(e)}", "danger")

    return redirect(url_for('admin_work_type'))

@app.route("/admin-work-category", methods=["GET", "POST"])
def admin_work_category():
    work_category_to_edit = None  # Initialize variable for editing

    if request.method == "POST":
        work_category_name = request.form['work_category']  # Get the Work Category name from the form
        work_category_id = request.form.get('work_category_id')  # Hidden field for the Work Category ID if editing

        if work_category_id:  # Update operation
            try:
                update_category_query = f"""
                UPDATE tbl_work_category 
                SET work_category_name = '{work_category_name}'
                WHERE id = {work_category_id}
                """
                db.execute(update_category_query)
                flash("Work Category updated successfully!", "success")
            except Exception as e:
                flash(f"Failed to update Work Category: {str(e)}", "danger")
        else:  # Create operation
            try:
                insert_category_query = f"""
                INSERT INTO tbl_work_category (work_category_name) 
                VALUES ('{work_category_name}')
                """
                db.single_insert(insert_category_query)
                flash("Work Category added successfully!", "success")
            except Exception as e:
                flash(f"Failed to add Work Category: {str(e)}", "danger")

        return redirect(url_for('admin_work_category'))

    # Check if there is an edit query parameter
    edit_id = request.args.get('edit')
    if edit_id:  # If an edit ID is present
        work_category_to_edit = db.fetchone(f"SELECT * FROM tbl_work_category WHERE id = {edit_id}")

    # Fetch all Work Categories to display in the table
    work_categories = db.fetchall("SELECT * FROM tbl_work_category")

    return render_template("admin/work_category.html", work_categories=work_categories, work_category_to_edit=work_category_to_edit)


@app.route("/delete-work-category/<int:work_category_id>", methods=["POST"])
def delete_work_category(work_category_id):
    try:
        delete_category_query = f"DELETE FROM tbl_work_category WHERE id = {work_category_id}"
        db.execute(delete_category_query)
        flash("Work Category deleted successfully!", "success")
    except Exception as e:
        flash(f"Failed to delete Work Category: {str(e)}", "danger")

    return redirect(url_for('admin_work_category'))


@app.route("/admin-work", methods=["GET", "POST"])
def admin_work():
    work_to_edit = None  # Initialize variable for editing

    if request.method == "POST":
        work_category_id = request.form['work_category_id']  # Get selected Work Category from the dropdown
        work_details = request.form['work_details']  # Get Work Details from the form
        work_id = request.form.get('work_id')  # Hidden field for Work ID if editing

        if work_id:  # Update operation
            try:
                update_work_query = f"""
                UPDATE tbl_work 
                SET work_category_id = {work_category_id}, work_details = '{work_details}'
                WHERE id = {work_id}
                """
                db.execute(update_work_query)
                flash("Work updated successfully!", "success")
            except Exception as e:
                flash(f"Failed to update Work: {str(e)}", "danger")
        else:  # Create operation
            try:
                insert_work_query = f"""
                INSERT INTO tbl_work (work_category_id, work_details) 
                VALUES ({work_category_id}, '{work_details}')
                """
                db.single_insert(insert_work_query)
                flash("Work added successfully!", "success")
            except Exception as e:
                flash(f"Failed to add Work: {str(e)}", "danger")

        return redirect(url_for('admin_work'))

    # Check if there's an edit query parameter
    edit_id = request.args.get('edit')
    if edit_id:  # If an edit ID is present
        work_to_edit = db.fetchone(f"SELECT * FROM tbl_work WHERE id = {edit_id}")

    # Fetch all Work and Work Categories to display in the table and dropdown
    work_categories = db.fetchall("SELECT * FROM tbl_work_category")
    works = db.fetchall("SELECT tbl_work.*, tbl_work_category.work_category_name FROM tbl_work JOIN tbl_work_category ON tbl_work.work_category_id = tbl_work_category.id")

    return render_template("admin/work.html", works=works, work_categories=work_categories, work_to_edit=work_to_edit)


@app.route("/open-work", methods=["GET", "POST"])
def open_work():
    works = db.fetchall("SELECT tbl_work.*, tbl_work_category.work_category_name FROM tbl_work JOIN tbl_work_category ON tbl_work.work_category_id = tbl_work_category.id where tbl_work.status=1 ")

    return render_template("admin/open_work.html", works=works)



@app.route("/closed-work", methods=["GET", "POST"])
def closed_work():
    works = db.fetchall("SELECT tbl_work.*, tbl_work_category.work_category_name FROM tbl_work JOIN tbl_work_category ON tbl_work.work_category_id = tbl_work_category.id where tbl_work.status=2 ")

    return render_template("admin/closed_work.html", works=works)



@app.route("/delete-work/<int:work_id>", methods=["POST"])
def delete_work(work_id):
    try:
        delete_work_query = f"DELETE FROM tbl_work WHERE id = {work_id}"
        db.execute(delete_work_query)
        flash("Work deleted successfully!", "success")
    except Exception as e:
        flash(f"Failed to delete work: {str(e)}", "danger")

    return redirect(url_for('admin_work'))

@app.route("/admin-mate", methods=["GET", "POST"])
def admin_mate():
    mate_to_edit = None  # Initialize variable for editing

    if request.method == "POST":
        username = request.form['username']  
        password = request.form['password'] 
        name = request.form['name'] 
        details = request.form['details'] 
        contact = request.form['contact'] 
        panchayat = request.form['panchayat'] 
        ward = request.form['ward']  
        mate_id = request.form.get('mate_id') 

        if mate_id:  # Update operation
            try:
                # Update tbl_mate
                update_mate_query = f"""
                UPDATE tbl_mate 
                SET name = '{name}', details = '{details}', contact = '{contact}', panchayat = '{panchayat}', ward = '{ward}' 
                WHERE id = {mate_id}
                """
                db.execute(update_mate_query)
                flash("Mate updated successfully!", "success")
            except Exception as e:
                flash(f"Failed to update mate: {str(e)}", "danger")
        else:  # Create operation
            try:
                # First, insert into tbl_login
                insert_login_query = f"""
                INSERT INTO tbl_login (username, password, type) 
                VALUES ('{username}', '{password}', 'mate')
                """
                

                # Get the last inserted login ID
                login_id = db.executeAndReturnId(insert_login_query)  # Assuming you have a method to get the last inserted ID

                # Now insert into tbl_mate
                insert_mate_query = f"""
                INSERT INTO tbl_mate (name, details, contact, panchayat, ward, login_id) 
                VALUES ('{name}', '{details}', '{contact}', '{panchayat}', '{ward}', {login_id})
                """
                db.single_insert(insert_mate_query)
                flash("Mate added successfully!", "success")
            except Exception as e:
                flash(f"Failed to add mate: {str(e)}", "danger")

        return redirect(url_for('admin_mate'))

    # Check if there's an edit query parameter
    edit_id = request.args.get('edit')
    if edit_id:  # If an edit ID is present
        mate_to_edit = db.fetchone(f"SELECT * FROM tbl_mate WHERE id = {edit_id}")

    # Fetch all mates to display in the table
    mates = db.fetchall("""
        SELECT tbl_mate.*, tbl_login.username 
        FROM tbl_mate 
        JOIN tbl_login ON tbl_mate.login_id = tbl_login.id
    """)

    # Fetch panchayats and wards from the database
    panchayats = db.fetchall("SELECT * FROM tbl_panchayat")  # Adjust according to your table name
    wards = db.fetchall("SELECT * FROM tbl_ward")  # Adjust according to your table name

    return render_template("admin/mate.html", mates=mates, mate_to_edit=mate_to_edit, panchayats=panchayats, wards=wards)

    
@app.route("/delete-mate/<int:mate_id>", methods=["POST"])
def delete_mate(mate_id):
    try:
        # First, get the login ID to delete from tbl_login
        login_id_query = f"SELECT login_id FROM tbl_mate WHERE id = {mate_id}"
        login_id = db.fetchone(login_id_query)['login_id']

        # Delete from tbl_mate
        delete_mate_query = f"DELETE FROM tbl_mate WHERE id = {mate_id}"
        db.execute(delete_mate_query)

        # Then delete from tbl_login
        delete_login_query = f"DELETE FROM tbl_login WHERE id = {login_id}"
        db.execute(delete_login_query)

        flash("Mate deleted successfully!", "success")
    except Exception as e:
        flash(f"Failed to delete mate: {str(e)}", "danger")

    return redirect(url_for('admin_mate'))

@app.route("/admin-landowner")
def admin_landowner():
    landowners=db.fetchall("select * from tbl_land_owner where status=1")
    return render_template("admin/land_owner.html",landowners=landowners)

@app.route("/admin-new-landowner")
def admin_new_landowner():
    type = request.args.get('type')
    landowner_id = request.args.get('landowner_id')
    print(f"type:{type}, landowner_id:{landowner_id}")
    try:
        if landowner_id:
            if type == 'accept':
                update_landowner_query = f"""
                        UPDATE tbl_land_owner
                        SET status =1  
                        WHERE login_id = {landowner_id}
                        """
            else:
                update_landowner_query = f"""
                        UPDATE tbl_land_owner 
                        SET status =2 
                        WHERE login_id = {landowner_id}
                        """
            db.execute(update_landowner_query)
    except Exception as e:
        print(f"exeption:{e}")
        flash(f"Failed to delete mate: {str(e)}", "danger")
    landowners=db.fetchall("select * from tbl_land_owner where status=0")
    return render_template("admin/land_owner.html", landowners=landowners)

@app.route("/admin-landowner-plots/<int:landowner_id>", methods=["GET","POST"])
def admin_landowner_plots(landowner_id):
    landowner=db.fetchone(f"select * from tbl_land_owner where login_id={landowner_id}")
    print(landowner)
    plots = db.fetchall(f"""
        SELECT tbl_plot.id, tbl_panchayat.panchayat_name, tbl_ward.ward_name, tbl_land_category.land_category_name,tbl_plot.plot_documents,tbl_plot.plot_details
        FROM tbl_plot
        INNER JOIN tbl_ward ON tbl_plot.ward_id = tbl_ward.id
        INNER JOIN tbl_panchayat ON tbl_ward.panchayat_id = tbl_panchayat.id
        INNER JOIN tbl_land_category ON tbl_plot.land_category_id = tbl_land_category.id where tbl_plot.land_owner_id={landowner_id}
    """)
    return render_template("admin/plot.html",plots=plots,landowner=landowner)





#land_owner

@app.route("/landowner-home")
def landownerhome():
    # Retrieve the logged-in landowner's ID from the session
    land_owner_id = session['user_id']
    
    # Query for total landowners, mates, and land works associated with the logged-in landowner
    total_plots = db.fetchone(f"SELECT COUNT(*) as count FROM tbl_plot where land_owner_id={land_owner_id}")['count']
    total_mates = db.fetchone("SELECT COUNT(*) as count FROM tbl_mate")['count']
    
    # Query total land works for the logged-in landowner
    total_land_works = db.fetchone(f"""
        SELECT COUNT(*) as count 
        FROM tbl_land_work 
        WHERE land_owner_id = {land_owner_id}
    """)['count']
    
    # Monthly land work count for the logged-in landowner
    land_works_by_month = db.fetchall(f"""
        SELECT MONTH(created_on) as month, COUNT(*) as count 
        FROM tbl_land_work
        WHERE land_owner_id = {land_owner_id} 
        GROUP BY MONTH(created_on)
        ORDER BY MONTH(created_on)
    """)

    # Work distribution by type for the logged-in landowner (if applicable)
    work_distribution = db.fetchall(f"""
        SELECT work_type_id, COUNT(*) as count 
        FROM tbl_land_work 
        WHERE land_owner_id = {land_owner_id}
        GROUP BY work_type_id
    """)

    return render_template(
        "land_owner/index.html", 
        total_plots=total_plots, 
        total_mates=total_mates,
        total_land_works=total_land_works,
        land_works_by_month=land_works_by_month,
        work_distribution=work_distribution
    )

# Set the directory to save the uploaded files
UPLOAD_FOLDER = 'static/doc'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

@app.route("/landowner-plot", methods=["GET", "POST"])
def landowner_plot():
    land_owner_id = session['user_id']
    if request.method == "POST":
        
        
        land_category_id = request.form['land_category_id']
        plot_details = request.form['plot_details']
        plot_documents = request.files['plot_documents']
        filename = plot_documents.filename
        ward_id = request.form['ward_id']
        plot_id = request.form.get('plot_id')  # Hidden field for plot ID if editing

        if plot_id:  # Update operation
            try:
                upd_doc=''
                if filename:
                    upd_doc=f"plot_documents = '{filename}', "
                    print('upd_doc')
                    print(upd_doc)
                    plot_documents.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
                update_plot_query = f"""
                UPDATE tbl_plot 
                SET 
                    land_owner_id = {land_owner_id}, 
                    land_category_id = {land_category_id}, 
                    plot_details = '{plot_details}', 
                    {upd_doc}
                    ward_id = {ward_id}
                WHERE id = {plot_id}
                """
                
                print('update_plot_query')
                print(update_plot_query)
                
                db.execute(update_plot_query)
                flash("Plot updated successfully!", "success")
            except Exception as e:
                flash(f"Failed to update plot: {str(e)}", "danger")
        else:  # Create operation
            try:
                insert_plot_query = f"""
                INSERT INTO tbl_plot (land_owner_id, land_category_id, plot_details, plot_documents, ward_id) 
                VALUES ({land_owner_id}, {land_category_id}, '{plot_details}', '{filename}', {ward_id})
                """
                db.single_insert(insert_plot_query)
                plot_documents.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
                flash("Plot added successfully!", "success")
            except Exception as e:
                flash(f"Failed to add plot: {str(e)}", "danger")

        return redirect(url_for('landowner_plot'))

    # Fetch plots and related data to display in the table
    plots = db.fetchall(f"""
        SELECT tbl_plot.id, tbl_panchayat.panchayat_name, tbl_ward.ward_name, tbl_land_category.land_category_name,tbl_plot.plot_documents,tbl_plot.plot_details
        FROM tbl_plot
        INNER JOIN tbl_ward ON tbl_plot.ward_id = tbl_ward.id
        INNER JOIN tbl_panchayat ON tbl_ward.panchayat_id = tbl_panchayat.id
        INNER JOIN tbl_land_category ON tbl_plot.land_category_id = tbl_land_category.id where tbl_plot.land_owner_id={land_owner_id}
    """)
    
    panchayats = db.fetchall("SELECT * FROM tbl_panchayat")
    wards = db.fetchall("SELECT w.*,p.panchayat_name FROM tbl_ward w join tbl_panchayat p on w.panchayat_id=p.id")
    land_owners = db.fetchall("SELECT * FROM tbl_land_owner")  # Assuming you have a land owner table
    land_categories = db.fetchall("SELECT * FROM tbl_land_category")

    plot_to_edit = None
    if 'edit' in request.args:
        plot_id = request.args.get('edit')
        plot_to_edit = db.fetchone(f"SELECT * FROM tbl_plot WHERE id = {plot_id}")

    return render_template("land_owner/plot.html", plots=plots, panchayats=panchayats, wards=wards, land_owners=land_owners, land_categories=land_categories, plot_to_edit=plot_to_edit)


@app.route("/delete-plot/<int:plot_id>", methods=["POST"])
def delete_plot(plot_id):
    try:
        delete_plot_query = f"DELETE FROM tbl_plot WHERE id = {plot_id}"
        db.execute(delete_plot_query)
        flash("Plot deleted successfully!", "success")
    except Exception as e:
        flash(f"Failed to delete plot: {str(e)}", "danger")

    return redirect(url_for('landowner_plot'))

@app.route("/landowner-work", methods=["GET", "POST"])
def landowner_work():
    land_owner_id = session['user_id']
    if request.method == "POST":
        plot_id = request.form['plot_id']  
        work_type_id = request.form['work_type_id']
        land_work_details = request.form['land_work_details']
        status = 'initiated'
        land_work_id = request.form.get('land_work_id')  

        if land_work_id:  
            try:
                update_work_query = f"""
                UPDATE tbl_land_work 
                SET 
                    plot_id = {plot_id}, 
                    land_owner_id = {land_owner_id}, 
                    work_type_id = {work_type_id}, 
                    land_work_details = '{land_work_details}'
                WHERE id = {land_work_id}
                """
                db.execute(update_work_query)
                flash("Land work updated successfully!", "success")
            except Exception as e:
                flash(f"Failed to update land work: {str(e)}", "danger")
        else:  # Create operation
            try:
                insert_work_query = f"""
                INSERT INTO tbl_land_work (plot_id, land_owner_id, work_type_id, land_work_details, status) 
                VALUES ({plot_id}, {land_owner_id}, {work_type_id}, '{land_work_details}', '{status}')
                """
                db.single_insert(insert_work_query)
                flash("Land work added successfully!", "success")
            except Exception as e:
                flash(f"Failed to add land work: {str(e)}", "danger")

        return redirect(url_for('landowner_work'))

    # Fetch land works and related data to display in the table
    land_works = db.fetchall(f"""
        SELECT lw.id, lw.land_work_details, lw.status, p.plot_details, ow.work_type_name
        FROM tbl_land_work lw
        INNER JOIN tbl_plot p ON lw.plot_id = p.id
        INNER JOIN tbl_work_type ow ON lw.work_type_id = ow.id where lw.land_owner_id={land_owner_id}
    """)

    plots = db.fetchall("SELECT * FROM tbl_plot")  # Fetch all plots
    work_types = db.fetchall("SELECT * FROM tbl_work_type")  # Fetch all work types

    land_work_to_edit = None
    if 'edit' in request.args:
        land_work_id = request.args.get('edit')
        land_work_to_edit = db.fetchone(f"SELECT * FROM tbl_land_work WHERE id = {land_work_id}")

    return render_template("land_owner/work.html", 
                           land_works=land_works, 
                           plots=plots, 
                           work_types=work_types, 
                           land_work_to_edit=land_work_to_edit)
    
@app.route("/landowner-ongoing-work", methods=["GET", "POST"])
def landowner_ongoing_work():
    land_owner_id = session['user_id']
    # Fetch land works and related data to display in the table
    land_works = db.fetchall(f"""
        SELECT m.name as mate_name,lw.id, lw.land_work_details, lw.status, p.plot_details, ow.work_type_name
        FROM tbl_land_work lw
        INNER JOIN tbl_plot p ON lw.plot_id = p.id
        INNER JOIN tbl_work_type ow ON lw.work_type_id = ow.id
        INNER JOIN tbl_mate_work mw ON mw.work_id = lw.id
        INNER JOIN tbl_mate m ON m.login_id=mw.mate_id
        where lw.land_owner_id={land_owner_id} and lw.status=1 and mw.work_type='land_work'
    """)

    return render_template("land_owner/ongoing_work.html",land_works=land_works)

@app.route("/landowner-closed-work", methods=["GET", "POST"])
def landowner_closed_work():
    land_owner_id = session['user_id']
    # Fetch land works and related data to display in the table
    land_works = db.fetchall(f"""
        SELECT m.name as mate_name,lw.id, lw.land_work_details, lw.status, p.plot_details, ow.work_type_name
        FROM tbl_land_work lw
        INNER JOIN tbl_plot p ON lw.plot_id = p.id
        INNER JOIN tbl_work_type ow ON lw.work_type_id = ow.id
        INNER JOIN tbl_mate_work mw ON mw.work_id = lw.id
        INNER JOIN tbl_mate m ON m.login_id=mw.mate_id
        where lw.land_owner_id={land_owner_id} and lw.status=2 and mw.work_type='land_work'
    """)

    return render_template("land_owner/closed_work.html",land_works=land_works)
    

@app.route("/delete-land-work/<int:land_work_id>", methods=["POST"])
def delete_land_work(land_work_id):
    try:
        delete_work_query = f"DELETE FROM tbl_land_work WHERE id = {land_work_id}"
        db.execute(delete_work_query)
        flash("Land work deleted successfully!", "success")
    except Exception as e:
        flash(f"Failed to delete land work: {str(e)}", "danger")

    return redirect(url_for('landowner_work'))



#mate

@app.route("/mate-home")
def matehome():
    # Fetch data for works count
    works_count = db.fetchone("SELECT COUNT(*) as total FROM tbl_mate_work WHERE status != 'closed'")['total']
    
    # Fetch data for attendance count
    attendance_count = db.fetchone("SELECT COUNT(*) as total FROM tbl_attendance")['total']
    
    # Optionally, fetch additional data for graphs
    # For example, count of works per status
    works_per_status = db.fetchall("""
        SELECT status, COUNT(*) as count 
        FROM tbl_mate_work 
        GROUP BY status
    """)
    
    return render_template("mate/index.html", 
                           works_count=works_count, 
                           attendance_count=attendance_count, 
                           works_per_status=works_per_status)


@app.route("/mate-workers", methods=["GET", "POST"])
def mate_workers():
    mate_id = session.get('user_id')  # Fetch mate_id from the session

    worker_to_edit = None  # Initialize variable for editing

    if request.method == "POST":
        name = request.form['name']  # Get worker's name
        workers_details = request.form['workers_details']  # Get worker details
        worker_id = request.form.get('worker_id')  # Hidden field for Worker ID if editing

        if worker_id:  # Update operation
            try:
                # Update tbl_workers
                update_worker_query = f"""
                UPDATE tbl_workers 
                SET name = '{name}', workers_details = '{workers_details}' 
                WHERE id = {worker_id} AND mate_id = {mate_id}
                """
                db.execute(update_worker_query)
                flash("Worker updated successfully!", "success")
            except Exception as e:
                flash(f"Failed to update worker: {str(e)}", "danger")
        else:  # Create operation
            try:
                # Insert into tbl_workers
                insert_worker_query = f"""
                INSERT INTO tbl_workers (mate_id, name, workers_details) 
                VALUES ({mate_id}, '{name}', '{workers_details}')
                """
                db.execute(insert_worker_query)  # Make sure to adjust based on your DB execution method
                flash("Worker added successfully!", "success")
            except Exception as e:
                flash(f"Failed to add worker: {str(e)}", "danger")

        return redirect(url_for('mate_workers'))

    # Check if there's an edit query parameter
    edit_id = request.args.get('edit')
    if edit_id:  # If an edit ID is present
        worker_to_edit = db.fetchone(f"SELECT * FROM tbl_workers WHERE id = {edit_id} AND mate_id = {mate_id}")

    # Fetch all workers associated with the mate
    workers = db.fetchall(f"""
        SELECT * FROM tbl_workers 
        WHERE mate_id = {mate_id}
    """)

    return render_template("mate/workers.html", workers=workers, worker_to_edit=worker_to_edit)

@app.route("/delete_worker/<int:worker_id>", methods=["POST"])
def delete_worker(worker_id):
    mate_id = session.get('mate_id')
    if mate_id is None:
        flash("You need to log in first.", "danger")
        return redirect(url_for('login'))

    try:
        # Delete from tbl_workers where mate_id matches
        delete_worker_query = f"""
        DELETE FROM tbl_workers 
        WHERE id = {worker_id} AND mate_id = {mate_id}
        """
        db.execute(delete_worker_query)
        flash("Worker deleted successfully!", "success")
    except Exception as e:
        flash(f"Failed to delete worker: {str(e)}", "danger")

    return redirect(url_for('mate_workers'))


@app.route("/mate-work", methods=["GET", "POST"])
def mate_work():
    works = db.fetchall("SELECT tbl_work.*, tbl_work_category.work_category_name FROM tbl_work JOIN tbl_work_category ON tbl_work.work_category_id = tbl_work_category.id where tbl_work.status=0")

    return render_template("mate/work.html", works=works)

@app.route("/mate-accept-work/<int:work_id>", methods=["POST"])
def mate_accept_work(work_id):
    try:
        mate_id = session.get('user_id')
        update_work_query = f"update tbl_work set status=1 WHERE id = {work_id}"
        db.execute(update_work_query)
        insert_work_query=f"INSERT INTO `tbl_mate_work`(`work_id`, `mate_id`, `work_type`, `status`) VALUES ({work_id},{mate_id},'work','accepted')"
        db.single_insert(insert_work_query)
        flash("Work accepted successfully!", "success")
    except Exception as e:
        flash(f"Failed to accept work: {str(e)}", "danger")

    return redirect(url_for('mate_work'))

@app.route("/mate-landowner-work", methods=["GET", "POST"])
def mate_landowner_work():

    # Fetch land works and related data to display in the table
    land_works = db.fetchall("""
        SELECT lw.id, lw.land_work_details, lw.status, p.plot_details, ow.work_type_name
        FROM tbl_land_work lw
        INNER JOIN tbl_plot p ON lw.plot_id = p.id
        INNER JOIN tbl_work_type ow ON lw.work_type_id = ow.id where lw.status=0
    """)

    return render_template("mate/landowner_work.html", 
                           land_works=land_works, 
                          )
    
@app.route("/mate-accept-landowner-work/<int:land_work_id>", methods=["POST"])
def accept_landowner_work(land_work_id):
    try:
        mate_id = session.get('user_id')
        update_work_query = f"update tbl_land_work set status=1 WHERE id = {land_work_id}"
        db.execute(update_work_query)
        insert_work_query=f"INSERT INTO `tbl_mate_work`(`work_id`, `mate_id`, `work_type`, `status`) VALUES ({land_work_id},{mate_id},'land_work','accepted')"
        # print(insert_work_query)
        db.single_insert(insert_work_query)
    except Exception as e:
        flash(f"Failed to accept land work: {str(e)}", "danger")

    return redirect(url_for('mate_landowner_work'))



@app.route("/mate-show-work", methods=["POST", "GET"])
def show_work():
    mate_id = session.get('user_id')
    works = db.fetchall(f"""
        SELECT mw.id as mw_id, w.*, wc.work_category_name 
        FROM tbl_mate_work mw 
        INNER JOIN tbl_work w ON w.id = mw.work_id 
        JOIN tbl_work_category wc ON w.work_category_id = wc.id 
        WHERE mw.mate_id = {mate_id} AND mw.status = 'accepted' AND mw.work_type = 'work'
    """)
    return render_template("mate/show_work.html", works=works)


@app.route("/mate-assignment-work/<int:mw_id>", methods=["POST", "GET"])
def mate_assignment_work(mw_id):
    mate_id = session.get('user_id')  # Fetch mate_id from session
    if not mate_id:
        flash("Please log in first.", "danger")
        return redirect(url_for('login'))

    # Fetch work details
    work = db.fetchone(f"""
        SELECT w.*, mw.id as mwid 
        FROM tbl_work w 
        INNER JOIN tbl_mate_work mw ON mw.work_id = w.id 
        WHERE mw.id = {mw_id}
    """)

    # Fetch all workers for the mate
    workers = db.fetchall(f"SELECT id, name, workers_details FROM tbl_workers WHERE mate_id = {mate_id}")

    # Fetch assigned workers for the work to pre-select checkboxes
    assigned_workers = db.fetchall(f"SELECT workers_id FROM tbl_work_assign WHERE mate_work_id = {mw_id}")
    assigned_workers_ids = [w['workers_id'] for w in assigned_workers]  # Create a list of assigned workers IDs

    if request.method == "POST":
        selected_workers = request.form.getlist('workers')  # Get list of selected workers from the form

        # Delete existing assignments for the work
        db.execute(f"DELETE FROM tbl_work_assign WHERE mate_work_id = {mw_id}")

        # Insert new assignments
        for worker_id in selected_workers:
            db.execute(f"INSERT INTO tbl_work_assign (mate_work_id, workers_id) VALUES ({mw_id}, {worker_id})")

        flash("Assignments updated successfully!", "success")
        return redirect(url_for('mate_assignment_work', mw_id=mw_id))

    # Render the template with the workers and work data
    return render_template("mate/mate_assignment_work.html", work=work, workers=workers, assigned_workers_ids=assigned_workers_ids)


@app.route("/mate-work-attendance/<int:mw_id>", methods=["POST", "GET"])
def mate_work_attendance(mw_id):
    mate_id = session.get('user_id')  # Fetch mate_id from session
    if not mate_id:
        flash("Please log in first.", "danger")
        return redirect(url_for('login'))

    # Fetch work details
    work = db.fetchone(f"""
        SELECT * FROM tbl_work w 
        INNER JOIN tbl_mate_work mw ON mw.work_id = w.id 
        WHERE mw.id = {mw_id}
    """)

    # Fetch all workers assigned to the work
    assigned_workers = db.fetchall(f"""
        SELECT w.id, w.name, w.workers_details 
        FROM tbl_workers w
        JOIN tbl_work_assign wa ON w.id = wa.workers_id
        WHERE wa.mate_work_id = {mw_id}
    """)

    if request.method == "POST":
        attendance_date = request.form.get("attendance_date")
        selected_workers = request.form.getlist('workers')  # Get list of selected workers' IDs for attendance

        # Ensure a date is provided
        if not attendance_date:
            flash("Please select a date.", "danger")
            return redirect(url_for('mate_work_attendance', mw_id=mw_id))

        # Insert attendance for selected workers, prevent duplicate entries
        try:
            for worker_id in selected_workers:
                # Check if the attendance entry for this worker, work, and date already exists
                existing_entry = db.fetchone(f"""
                    SELECT * FROM tbl_attendance 
                    WHERE workers_id = {worker_id} AND mate_work_id = {mw_id} AND date = '{attendance_date}'
                """)

                if not existing_entry:
                    # If no existing entry, insert new attendance record
                    db.single_insert(f"""
                        INSERT INTO tbl_attendance (workers_id, mate_work_id, date)
                        VALUES ({worker_id}, {mw_id}, '{attendance_date}')
                    """)

            flash("Attendance successfully recorded.", "success")
        except Exception as e:
            flash(f"Failed to record attendance: {str(e)}", "danger")

        return redirect(url_for('mate_work_attendance', mw_id=mw_id))

    return render_template("mate/mate_work_attendance.html", work=work, workers=assigned_workers)


@app.route("/work-attendance/<int:mw_id>", methods=["GET"])
def work_attendance(mw_id):
    mate_id = session.get('user_id')  # Fetch mate_id from session
    if not mate_id:
        flash("Please log in first.", "danger")
        return redirect(url_for('login'))

    # Fetch work details
    work = db.fetchone(f"""
        SELECT * FROM tbl_work w 
        INNER JOIN tbl_mate_work mw ON mw.work_id = w.id 
        WHERE mw.id = {mw_id}
    """)

    # Fetch all workers who were marked as present for this work
    attendance_records = db.fetchall(f"""
        SELECT w.id, w.name, w.workers_details, a.date 
        FROM tbl_attendance a
        JOIN tbl_workers w ON a.workers_id = w.id
        WHERE a.mate_work_id = {mw_id}
        ORDER BY a.date DESC
    """)

    return render_template("mate/work_attendance.html", work=work, attendance_records=attendance_records)

@app.route("/work-close/<int:mw_id>", methods=["GET"])
def work_close(mw_id):
    # Update the status of the mate work to 'closed'
    db.execute(f"UPDATE tbl_mate_work SET status='closed' WHERE id={mw_id}")

    # Fetch the associated work_id for the mate work
    work_id = db.fetchone(f"SELECT work_id FROM tbl_mate_work WHERE id={mw_id}")
    
    # Ensure work_id is retrieved correctly
    if work_id:
        work_id = work_id['work_id']  # Extract the work_id from the fetched result
        # Update the status of the work to '2'
        db.execute(f"UPDATE tbl_work SET status=2 WHERE id={work_id}")

    flash("Work closed successfully!", "success")
    return redirect(url_for("show_closed_work"))  

@app.route("/mate-show-closed-work", methods=["POST", "GET"])
def show_closed_work():
    mate_id = session.get('user_id')
    works = db.fetchall(f"""
        SELECT mw.id as mw_id, w.*, wc.work_category_name 
        FROM tbl_mate_work mw 
        INNER JOIN tbl_work w ON w.id = mw.work_id 
        JOIN tbl_work_category wc ON w.work_category_id = wc.id 
        WHERE mw.mate_id = {mate_id} AND mw.status = 'closed' AND mw.work_type = 'work'
    """)
    return render_template("mate/show_closed_work.html", works=works)





@app.route("/mate-show-land-work", methods=["POST", "GET"])
def show_land_work():
    mate_id = session.get('user_id')
    land_works = db.fetchall(f"""
        SELECT mw.id as mw_id,lw.id, lw.land_work_details, lw.status, p.plot_details, ow.work_type_name 
        FROM tbl_mate_work mw 
        INNER JOIN tbl_land_work lw ON lw.id = mw.work_id 
        INNER JOIN tbl_plot p ON lw.plot_id = p.id 
        INNER JOIN tbl_work_type ow ON lw.work_type_id = ow.id 
        WHERE work_type='land_work' AND mw.mate_id={mate_id} AND mw.status='accepted'
    """)
    return render_template("mate/show_land_work.html", land_works=land_works)

@app.route("/mate-assignment-land-work/<int:mw_id>", methods=["POST", "GET"])
def mate_assignment_land_work(mw_id):
    mate_id = session.get('user_id')
    if not mate_id:
        flash("Please log in first.", "danger")
        return redirect(url_for('login'))

    # Fetch land work details using mw_id
    work = db.fetchone(f"""
        SELECT  mw.id as mw_id,lw.* FROM tbl_land_work lw
        INNER JOIN tbl_mate_work mw ON lw.id = mw.work_id
        WHERE mw.id={mw_id}
    """)

    # Fetch all workers for the mate
    workers = db.fetchall(f"SELECT id, name, workers_details FROM tbl_workers WHERE mate_id={mate_id}")

    # Fetch assigned workers for the land work using mw_id
    assigned_workers = db.fetchall(f"SELECT workers_id FROM tbl_work_assign WHERE mate_work_id={mw_id}")
    assigned_workers_ids = [w['workers_id'] for w in assigned_workers]

    if request.method == "POST":
        selected_workers = request.form.getlist('workers')

        # Delete existing assignments for the land work
        db.execute(f"DELETE FROM tbl_work_assign WHERE mate_work_id={mw_id}")

        # Insert new assignments
        for worker_id in selected_workers:
            db.execute(f"INSERT INTO tbl_work_assign (mate_work_id, workers_id) VALUES ({mw_id}, {worker_id})")

        flash("Assignments updated successfully!", "success")
        return redirect(url_for('mate_assignment_land_work', mw_id=mw_id))

    return render_template("mate/mate_assignment_land_work.html", work=work, workers=workers, assigned_workers_ids=assigned_workers_ids)

@app.route("/mate-land-work-attendance/<int:mw_id>", methods=["POST", "GET"])
def mate_land_work_attendance(mw_id):
    mate_id = session.get('user_id')
    if not mate_id:
        flash("Please log in first.", "danger")
        return redirect(url_for('login'))

    # Fetch land work details using mw_id
    work = db.fetchone(f"""
        SELECT lw.* FROM tbl_land_work lw
        INNER JOIN tbl_mate_work mw ON lw.id = mw.work_id
        WHERE mw.id={mw_id}
    """)

    # Fetch all workers assigned to the land work
    assigned_workers = db.fetchall(f"""
        SELECT w.id, w.name, w.workers_details 
        FROM tbl_workers w
        JOIN tbl_work_assign lwa ON w.id = lwa.workers_id
        WHERE lwa.mate_work_id = {mw_id}
    """)

    if request.method == "POST":
        attendance_date = request.form.get("attendance_date")
        selected_workers = request.form.getlist('workers')

        if not attendance_date:
            flash("Please select a date.", "danger")
            return redirect(url_for('mate_land_work_attendance', mw_id=mw_id))

        try:
            for worker_id in selected_workers:
                existing_entry = db.fetchone(f"""
                    SELECT * FROM tbl_attendance 
                    WHERE workers_id = {worker_id} AND mate_work_id = {mw_id} AND date = '{attendance_date}'
                """)

                if not existing_entry:
                    db.single_insert(f"""
                        INSERT INTO tbl_attendance (workers_id, mate_work_id, date)
                        VALUES ({worker_id}, {mw_id}, '{attendance_date}')
                    """)

            flash("Attendance successfully recorded.", "success")
        except Exception as e:
            flash(f"Failed to record attendance: {str(e)}", "danger")

        return redirect(url_for('mate_land_work_attendance', mw_id=mw_id))

    return render_template("mate/mate_land_work_attendance.html", work=work, workers=assigned_workers)

@app.route("/land-work-attendance/<int:mw_id>", methods=["GET"])
def land_work_attendance(mw_id):
    mate_id = session.get('user_id')
    if not mate_id:
        flash("Please log in first.", "danger")
        return redirect(url_for('login'))

    # Fetch land work details using mw_id
    work = db.fetchone(f"""
        SELECT lw.* FROM tbl_land_work lw
        INNER JOIN tbl_mate_work mw ON lw.id = mw.work_id
        WHERE mw.id={mw_id}
    """)

    # Fetch attendance records for the land work
    attendance_records = db.fetchall(f"""
        SELECT w.id, w.name, w.workers_details, a.date 
        FROM tbl_attendance a
        JOIN tbl_workers w ON a.workers_id = w.id
        WHERE a.mate_work_id = {mw_id}
        ORDER BY a.date DESC
    """)

    return render_template("mate/land_work_attendance.html", work=work, attendance_records=attendance_records)


@app.route("/work-land-close/<int:mw_id>", methods=["GET"])
def work_land_close(mw_id):
    
    db.execute(f"UPDATE tbl_mate_work SET status='closed' WHERE id={mw_id}")

    
    work_id = db.fetchone(f"SELECT work_id FROM tbl_mate_work WHERE id={mw_id}")
    
   
    if work_id:
        work_id = work_id['work_id']  
       
        db.execute(f"UPDATE tbl_land_work SET status=2 WHERE id={work_id}")

    flash("Work closed successfully!", "success")
    return redirect(url_for("show_closed_land_work"))  

@app.route("/mate-show-closed-land-work", methods=["POST", "GET"])
def show_closed_land_work():
    mate_id = session.get('user_id')
    land_works = db.fetchall(f"""
        SELECT mw.id as mw_id,lw.id, lw.land_work_details, lw.status, p.plot_details, ow.work_type_name 
        FROM tbl_mate_work mw 
        INNER JOIN tbl_land_work lw ON lw.id = mw.work_id 
        INNER JOIN tbl_plot p ON lw.plot_id = p.id 
        INNER JOIN tbl_work_type ow ON lw.work_type_id = ow.id 
        WHERE work_type='land_work' AND mw.mate_id={mate_id} AND mw.status='accepted'
    """)
    return render_template("mate/show_closed_land_work.html", land_works=land_works)

@app.route("/attendance-report", methods=["GET", "POST"])
def attendance_report():
    current_year = datetime.now().year  # Get the current year
    year = current_year  # Set the default year to current year
    total_attendance = 0
    yearwise_attendance = []
    individual_attendance = []  

    if request.method == "POST":
        year = request.form.get("year", type=int)  # Get the selected year, ensure it's an integer
        
        try:
            # Fetch total attendance for the selected year
            total_attendance = db.fetchone(f"""
                SELECT COUNT(*) as total FROM tbl_attendance 
                WHERE YEAR(date) = {year}
            """)['total']

            # Fetch year-wise attendance counts
            yearwise_attendance = db.fetchall("""
                SELECT YEAR(date) as year, COUNT(*) as total 
                FROM tbl_attendance 
                GROUP BY YEAR(date)
                ORDER BY YEAR(date)
            """)

            # Fetch individual attendance counts for the selected year
            individual_attendance = db.fetchall(f"""
                SELECT workers_id,name, COUNT(*) as attendance_count 
                FROM tbl_attendance a inner join tbl_workers w on w.id=a.workers_id
                WHERE YEAR(date) = {year}
                GROUP BY workers_id
            """)

        except Exception as e:
            print(f"Error fetching attendance data: {e}")
            total_attendance = 0
            yearwise_attendance = []
            individual_attendance = []

    return render_template("mate/attendance_report.html", 
                           total_attendance=total_attendance, 
                           yearwise_attendance=yearwise_attendance,
                           individual_attendance=individual_attendance,
                           selected_year=year,
                           current_year=current_year)
    
    
@app.route("/salary-report")
def salary_report():
    mate_id = session.get('user_id') 
    rate_per_day = 150

    if not mate_id:
        return "Error: Mate ID not found", 403

   
    attendance_counts = db.fetchall(f"""
        SELECT  tbl_attendance.workers_id,tbl_workers.name as workers_name,tbl_workers.workers_details, COUNT(tbl_attendance.date) AS days_worked
        FROM tbl_attendance
        JOIN tbl_mate_work ON tbl_mate_work.work_id = tbl_attendance.mate_work_id
        inner join tbl_workers on tbl_workers.id=tbl_attendance.workers_id
        WHERE tbl_mate_work.mate_id = {mate_id}
        GROUP BY tbl_attendance.workers_id
    """)

   
    print(attendance_counts)

   
    salaries = []
    for worker in attendance_counts:
      
        worker_id = worker['workers_id']
        workers_name=worker['workers_name']
        workers_details=worker['workers_details']
        days_worked = worker['days_worked'] 
        try:
            days = int(days_worked) 
            salary = days * rate_per_day  
            salaries.append({
                'workers_name': workers_name,
                'workers_details':workers_details,
                'days_worked': days,
                'salary': salary
            })
        except ValueError:
           
            print(f"Invalid days_worked value for worker {worker_id}: {days_worked}")

    return render_template("mate/salary_report.html", salaries=salaries)












# running application 
if __name__ == '__main__': 
    app.run(debug=True) 