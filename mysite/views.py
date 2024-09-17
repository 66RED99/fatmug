from django.shortcuts import render, get_object_or_404, redirect, HttpResponse
from django.contrib.auth.decorators import login_required
from .forms import VideoForm
from .models import Video, Subtitle, SubtitleText
from django.conf import settings
import os 
import ffmpeg
import glob
import re
from datetime import timedelta
from django.db.models import Q
import ffmpeg

def home_view(request):
    videos = Video.objects.select_related('uploaded_by').all()
    context = {"videos" : videos}
    return render(request, 'mysite/home.html', context)


def video_view(request, id):
    video = get_object_or_404(Video, id = id)
    subtitles = video.subtitle.all()
    context = { "video" : video, 'subtitles' : subtitles}
    return render(request, 'mysite/video.html', context)

def convert_to_timedelta(time_str):
    minutes, seconds = time_str.split(':')
    seconds, milliseconds = divmod(float(seconds), 1)
    return timedelta(minutes=int(minutes), seconds=int(seconds), milliseconds=int(milliseconds * 1000))

def parse_vtt(subtitle_file, subtitle_obj):
    # Updated regex to capture 'mm:ss.sss --> mm:ss.sss' format
    pattern = r'(\d{2}:\d{2}\.\d{3}) --> (\d{2}:\d{2}\.\d{3})\n([\s\S]+?)\n\n'
    
    with open(subtitle_file, 'r', encoding='utf-8') as file:
        content = file.read()
        matches = re.findall(pattern, content)

        if not matches:
            print("No matches found. Check if the subtitle format is correct.")
        else:
            print(f"Found {len(matches)} matches")

        for match in matches:
            start_time = match[0]
            end_time = match[1]
            text = match[2].strip()  # Strip unnecessary whitespace

            # Convert times to timedelta
            start_time = convert_to_timedelta(start_time)
            end_time = convert_to_timedelta(end_time)

            # Create SubtitleText entry
            s = SubtitleText.objects.create(subtitle=subtitle_obj, start_time=start_time, end_time=end_time, text=text)
            print("Created SubtitleText:", s)

def extract_subs(video):
    try:
        input_video = video.file.path
        output_dir = os.path.join(settings.MEDIA_ROOT, 'subs', str(video.id))
        os.makedirs(output_dir, exist_ok=True)
        
        probe = ffmpeg.probe(input_video)
        input = ffmpeg.input(input_video)
        subtitle_streams = [stream for stream in probe['streams'] if stream['codec_type']=='subtitle']
        
        for subtitle in subtitle_streams:
            language = subtitle['tags'].get('language', 'NULL')
            output_file = os.path.join(output_dir, f"{language}.vtt")
            output = ffmpeg.output(input, output_file, c='webvtt', map=f"0:{subtitle['index']}")
            ffmpeg.run(output, overwrite_output=True)

            # Save Subtitle object
            output_file = os.path.relpath(output_file, settings.MEDIA_ROOT)
            subtitle_obj = Subtitle.objects.create(video=video, file=output_file, language=language)
            
            # Parse and save subtitle texts
            parse_vtt(os.path.join(settings.MEDIA_ROOT, output_file), subtitle_obj)

    except ffmpeg.Error as e:
        print(e)



@login_required(login_url='/admin/login/')
def upload_view(request):
    if request.method == 'POST':
        form = VideoForm(request.POST, request.FILES)
        if form.is_valid():
            video = form.save(commit=False)
            video.uploaded_by = request.user
            video.save()
            
            extract_subs(video)
            
            return redirect('video', video.id)     
        else:
            print(form.errors)
    else:
        form = VideoForm()
    context = {"form" : form}
    return render(request, 'mysite/upload.html', context)


def search_view(request):
    query = request.GET.get('q', '')
    language = request.GET.get('language', '')  # Optional language filter
    video_id = request.GET.get('video_id', '')  # Filter by specific video
    video = get_object_or_404(Video, id=video_id)
    subtitles = video.subtitle.all()
    
    # Filter subtitles based on the search query and optionally by language and video
    subtitle_texts = SubtitleText.objects.filter(text__icontains=query)
    print(f"Search Query: {query}, Language Filter: {language}, Video ID: {video_id}, Filtered Subtitle Texts: {subtitle_texts}")

    if language:
        subtitle_texts = subtitle_texts.filter(subtitle__language=language)
    if video_id:
        subtitle_texts = subtitle_texts.filter(subtitle__video_id=video_id)

    context = {
        'query': query,
        'subtitle_texts': subtitle_texts,
        'video' : video,
        'subtitles' : subtitles
    }
    return render(request, 'mysite/video.html', context)