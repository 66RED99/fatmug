from django.db import models
from django.contrib.auth.models import User


class Video(models.Model):
    title = models.CharField(max_length=50)
    file = models.FileField(upload_to= 'videos/')
    uploaded_by = models.ForeignKey(User, related_name="videos", on_delete=models.CASCADE)
    uploaded_date = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return self.title
    
class Subtitle(models.Model):
    video = models.ForeignKey(Video, related_name="subtitle", on_delete=models.CASCADE) 
    file = models.FileField(upload_to='subs')
    language = models.CharField(max_length=50, default=None)
    
    def __str__(self):
        return f"{self.video.title} : {self.language}"
    
class SubtitleText(models.Model):
    subtitle = models.ForeignKey(Subtitle, related_name="texts", on_delete=models.CASCADE)
    start_time = models.DurationField()  
    end_time = models.DurationField()    
    text = models.TextField()          
    
    def __str__(self):
        return f"{self.subtitle} - {self.start_time}:{self.end_time}"
      