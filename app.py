from flask import Flask, render_template, request, url_for, flash, redirect
from flask_sqlalchemy import SQLAlchemy
from flask_bcrypt import Bcrypt
from flask_login import LoginManager, UserMixin, login_user, current_user, logout_user, login_required
from config import Config
from models import *
from forms import SponsorRegistrationForm,InfluencerRegistrationForm, LoginForm, CampaignForm

app = Flask(__name__)
app.config.from_object(Config)
db.init_app(app)
bcrypt = Bcrypt(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'
login_manager.login_message_category = 'info'

# Load user callback for Flask-Login
@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

@app.route("/")
@app.route("/home")
def home():
    return render_template('home.html')

# Login route
@app.route('/login', methods=['GET', 'POST'])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        # Get the form data
        username = form.username.data
        password = form.password.data

        # Find the user by username
        user = User.query.filter_by(username=username).first()

        # Use bcrypt to compare hashed password
        if user and bcrypt.check_password_hash(user.password, password):
            # Log the user in
            login_user(user)
            # Redirect based on role
            return redirect(url_for('dashboard'))
        else:
            flash('Invalid username or password', 'danger')

    return render_template('login.html', form=form)

# Dashboard route
@app.route('/dashboard')
@login_required
def dashboard():
    if current_user.is_authenticated:
        if current_user.role == 'Admin':
            return render_template('admin_dashboard.html')
        elif current_user.role == 'Sponsor':
            return render_template('sponsor_dashboard.html')
        elif current_user.role == 'Influencer':
            return render_template('influencer_dashboard.html')
    return redirect(url_for('home'))

@app.route('/profile')
@login_required
def profile():
    if current_user.is_authenticated:
        if current_user.role == 'Admin':
            return render_template('admin_profile.html')
        elif current_user.role == 'Sponsor':
            return render_template('sponsor_profile.html')
        elif current_user.role == 'Influencer':
            return render_template('influencer_profile.html')
    return redirect(url_for('home'))

@app.route("/register/sponsor", methods=['GET', 'POST'])
def sponsor_register():
    form = SponsorRegistrationForm()
    if form.validate_on_submit():
        hashed_password = bcrypt.generate_password_hash(form.password.data).decode('utf-8')
        user = User(username=form.username.data, email=form.email.data, password=hashed_password, role='sponsor')
        db.session.add(user)
        db.session.commit()
        sponsor = Sponsor(user_id=user.id, company_name=form.company_name.data, industry=form.industry.data, budget=form.budget.data)
        db.session.add(sponsor)
        db.session.commit()
        flash('Your sponsor account has been created!', 'success')
        return redirect(url_for('login'))
    return render_template('sponsor_register.html', title='Register Sponsor', form=form)

@app.route("/register/influencer", methods=['GET', 'POST'])
def influencer_register():
    form = InfluencerRegistrationForm()
    if form.validate_on_submit():
        hashed_password = bcrypt.generate_password_hash(form.password.data).decode('utf-8')
        user = User(username=form.username.data, email=form.email.data, password=hashed_password, role='influencer')
        db.session.add(user)
        db.session.commit()
        influencer = Influencer(user_id=user.id, name=form.name.data, category=form.category.data, niche=form.niche.data, reach=form.reach.data)
        db.session.add(influencer)
        db.session.commit()
        flash('Your influencer account has been created!', 'success')
        return redirect(url_for('login'))
    return render_template('influencer_register.html', title='Register Influencer', form=form)

@app.route("/logout")
def logout():
    logout_user()
    return redirect(url_for('home'))


@app.route("/campaign/new", methods=['GET', 'POST'])
@login_required
def create_campaign():
    form = CampaignForm()
    if form.validate_on_submit():
        campaign = Campaign(name=form.name.data, description=form.description.data, start_date=form.start_date.data,
                            end_date=form.end_date.data, budget=form.budget.data, visibility=form.visibility.data,
                            goals=form.goals.data, sponsor_id=current_user.id)
        db.session.add(campaign)
        db.session.commit()
        flash('Your campaign has been created!', 'success')
        return redirect(url_for('dashboard'))
    return render_template('create_campaign.html', title='New Campaign', form=form)


@app.route('/admin/dashboard')
def admin_dashboard():
    # Add logic to retrieve statistics and user data
    return render_template('admin_dashboard.html')

@app.route("/sponsor_dashboard")
# @login_required
def sponsor_dashboard():
    if current_user.role != 'sponsor':
        flash('Access denied!', 'danger')
        return redirect(url_for('home'))
    
    campaigns = Campaign.query.filter_by(user_id=current_user.id).all()
    ad_requests = AdRequest.query.filter_by(sponsor_id=current_user.id).all()
    return render_template('sponsor_dashboard.html', campaigns=campaigns, ad_requests=ad_requests)

@app.route("/campaign_detail/<int:campaign_id>", methods=['GET', 'POST'])
@login_required
def campaign_detail(campaign_id):
    campaign = Campaign.query.get_or_404(campaign_id)
    
    # Ensure only the campaign's sponsor can access the page
    if campaign.user_id != current_user.id:
        flash('Access denied!', 'danger')
        return redirect(url_for('sponsor_dashboard'))
    
    influencers = []
    
    if request.method == 'POST':
        search_query = request.form.get('search_query')
        # Search influencers based on name, category, or niche
        influencers = Influencer.query.filter(
            (Influencer.name.ilike(f"%{search_query}%")) |
            (Influencer.category.ilike(f"%{search_query}%")) |
            (Influencer.niche.ilike(f"%{search_query}%"))
        ).all()
    
    return render_template('campaign_detail.html', campaign=campaign, influencers=influencers)

@app.route("/influencer_detail/<int:influencer_id>")
@login_required
def influencer_detail(influencer_id):
    influencer = Influencer.query.get_or_404(influencer_id)
    return render_template('influencer_detail.html', influencer=influencer)

@app.route("/send_ad_request/<int:campaign_id>/<int:influencer_id>", methods=['POST'])
@login_required
def send_ad_request(campaign_id, influencer_id):
    campaign = Campaign.query.get_or_404(campaign_id)
    
    # Ensure only the campaign's sponsor can send requests
    if campaign.user_id != current_user.id:
        flash('Access denied!', 'danger')
        return redirect(url_for('sponsor_dashboard'))
    
    influencer = Influencer.query.get_or_404(influencer_id)
    
    # Create a new ad request for the selected influencer
    ad_request = AdRequest(
        campaign_id=campaign.id,
        influencer_id=influencer.id,
        status='Pending',
        requirements='',  # Customize requirements if needed
        payment_amount=0.0  # Set initial payment amount or customize
    )
    
    db.session.add(ad_request)
    db.session.commit()
    
    flash('Ad request sent successfully!', 'success')
    return redirect(url_for('campaign_detail', campaign_id=campaign.id))

@app.route("/ad_request_detail/<int:ad_request_id>")
# @login_required
def ad_request_detail(ad_request_id):
    ad_request = AdRequest.query.get_or_404(ad_request_id)
    if ad_request.sponsor_id != current_user.id:
        flash('Access denied!', 'danger')
        return redirect(url_for('sponsor_dashboard'))
    return render_template('ad_request_detail.html', ad_request=ad_request)

@app.route('/sponsor/ad_request/<int:ad_request_id>/edit', methods=['GET', 'POST'])
def edit_ad_request(ad_request_id):
    ad_request = AdRequest.query.get_or_404(ad_request_id)
    form = AdRequestForm(obj=ad_request)
    if form.validate_on_submit():
        ad_request.influencer_id = form.influencer_id.data
        ad_request.requirements = form.requirements.data
        ad_request.payment_amount = form.payment_amount.data
        ad_request.status = form.status.data
        db.session.commit()
        flash('Ad request updated successfully.', 'success')
        return redirect(url_for('ad_request_detail', ad_request_id=ad_request_id))
    return render_template('edit_ad_request.html', form=form, ad_request=ad_request)

@app.route('/sponsor/ad_request/<int:ad_request_id>/delete', methods=['POST'])
def delete_ad_request(ad_request_id):
    ad_request = AdRequest.query.get_or_404(ad_request_id)
    db.session.delete(ad_request)
    db.session.commit()
    flash('Ad request deleted successfully.', 'success')
    return redirect(url_for('campaign_details', campaign_id=ad_request.campaign_id))

@app.route('/influencer_dashboard')
@login_required
def influencer_dashboard():
    # Assuming `current_user` is the logged-in influencer
    influencer = Influencer.query.filter_by(username=current_user.username).first_or_404()

    # Fetch active campaigns the influencer is part of
    active_campaigns = Campaign.query.join(AdRequest).filter(
        AdRequest.influencer_id == influencer.id,
        AdRequest.status == 'Accepted'
    ).all()

    # Fetch pending ad requests
    pending_requests = AdRequest.query.filter_by(
        influencer_id=influencer.id,
        status='Pending'
    ).all()

    return render_template(
        'influencer_dashboard.html',
        influencer=influencer,
        active_campaigns=active_campaigns,
        pending_requests=pending_requests,
    )

@app.route('/search_campaigns', methods=['GET', 'POST'])
@login_required
def search_campaigns():
    search_results = []
    if request.method == 'POST':
        search_query = request.form.get('search_query')

        # Search for public campaigns matching the search query
        search_results = Campaign.query.filter(
            Campaign.visibility == 'Public',  # Ensure only public campaigns are shown
            db.or_(
                Campaign.name.ilike(f'%{search_query}%'),
                Campaign.description.ilike(f'%{search_query}%'),
                Campaign.niche.ilike(f'%{search_query}%')
            )
        ).all()

    return render_template('search_campaigns.html', search_results=search_results)

@app.route('/campaign_details/<int:campaign_id>', methods=['GET'])
@login_required
def campaign_details_influencer(campaign_id):
    campaign = Campaign.query.get_or_404(campaign_id)
    
    return render_template('campaign_details_influencer.html', campaign=campaign)

@app.route('/create_ad_request/<int:campaign_id>', methods=['POST'])
@login_required
def create_ad_request(campaign_id):
    campaign = Campaign.query.get_or_404(campaign_id)

    # Ensure the campaign is public
    if campaign.visibility != 'Public':
        flash("You cannot create an ad request for this campaign.", "danger")
        return redirect(url_for('search_campaigns'))

    requirements = request.form.get('requirements')
    payment_amount = request.form.get('payment_amount', type=float)
    message = request.form.get('message')

    # Create a new ad request
    ad_request = AdRequest(
        campaign_id=campaign.id,
        influencer_id=current_user.id,
        requirements=requirements,
        payment_amount=payment_amount,
        status='Pending',
        message=message
    )
    db.session.add(ad_request)
    db.session.commit()

    flash('Ad request created successfully!', 'success')
    return redirect(url_for('campaign_details_influencer', campaign_id=campaign.id))



@app.route('/campaigns')
def all_campaigns():
    # Add logic to retrieve all campaigns
    return render_template('all_campaigns.html')

@app.route('/campaigns/<int:campaign_id>')
def campaign_details(campaign_id):
    # Add logic to retrieve campaign details
    return render_template('campaign_details.html')

@app.route('/ad_requests')
def ad_requests():
    # Add logic to retrieve ad requests
    return render_template('ad_requests.html')



@app.route('/profile/influencer')
def influencer_profile():
    # Add logic to retrieve and update influencer profile
    return render_template('influencer_profile.html')

@app.route('/profile/sponsor')
def sponsor_profile():
    # Add logic to retrieve and update sponsor profile
    return render_template('sponsor_profile.html')

@app.route('/stats')
def stats_overview():
    # Add logic to retrieve and display stats
    return render_template('stats_overview.html')

# @app.route('/admin/login', methods=['GET', 'POST'])
# def admin_login():
#     form = AdminLoginForm()
#     if form.validate_on_submit():
#         # Handle login logic
#         return redirect(url_for('admin_dashboard'))
#     return render_template('admin_login.html', form=form)

# @app.route('/campaigns/new', methods=['GET', 'POST'])
# def new_campaign():
#     form = CreateCampaignForm()
#     if form.validate_on_submit():
#         # Handle campaign creation logic
#         return redirect(url_for('all_campaigns'))
#     return render_template('create_campaign.html', form=form)

