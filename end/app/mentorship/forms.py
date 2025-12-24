from flask_wtf import FlaskForm
from wtforms import StringField, TextAreaField, SubmitField, IntegerField, SelectField, DateTimeField
from wtforms.validators import DataRequired, Length


class ProfileForm(FlaskForm):
    academic_year = StringField('Academic Year')
    course = StringField('Course')
    interests = TextAreaField('Interests')
    goals = TextAreaField('Goals')
    submit = SubmitField('Save')


class MentorProfileForm(FlaskForm):
    title = StringField('Title')
    skills = StringField('Skills (comma separated)')
    years_of_experience = IntegerField('Years of Experience')
    hourly_rate = StringField('Hourly Rate')
    profile_pic = StringField('Profile picture URL')
    submit = SubmitField('Save')


class BookingForm(FlaskForm):
    topic = StringField('Topic', validators=[DataRequired(), Length(max=256)])
    description = TextAreaField('Description')
    scheduled_at = DateTimeField('Scheduled at (YYYY-MM-DD HH:MM)', format='%Y-%m-%d %H:%M', validators=[DataRequired()])
    submit = SubmitField('Request Session')


class MessageForm(FlaskForm):
    content = TextAreaField('Message', validators=[DataRequired(), Length(max=2000)])
    submit = SubmitField('Send')


class ReviewForm(FlaskForm):
    rating = SelectField('Rating', choices=[(str(i), str(i)) for i in range(1, 6)], validators=[DataRequired()])
    comment = TextAreaField('Comment')
    submit = SubmitField('Submit Review')
