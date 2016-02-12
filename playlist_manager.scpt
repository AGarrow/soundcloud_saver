on run argv
  set sc_user to item 1 of argv
  set sc_playlist to item 2 of argv
  set track_filepath to item 3 of argv as POSIX file
  set track_name to item 4 of argv
  
  log track_filepath

  tell application "iTunes"

    if not (exists folder playlist "SoundCloud") then
      set root_folder to make folder playlist with properties{name:"SoundCloud"}
    end if
    
    if not (exists folder playlist sc_user) then
      make folder playlist at folder playlist "SoundCloud" with properties{name:sc_user}
    end if 
    
    if not (exists playlist sc_playlist) then
      make new playlist at folder playlist sc_user with properties{name:sc_playlist}
    end if
    
    set track_id to add track_filepath
    
    if not exists (track track_name of playlist sc_playlist) then
      copy track_id to end of user playlist sc_playlist
    end
  end tell
end run