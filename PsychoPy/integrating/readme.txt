- The script is currently using the 2D dilation (could later add/shift the 3d function)
- outputs a plot & 4 CSVs
- plot: timeline with chord bin on the x-axis, dilation on the y-axis
- CSVs: 
	*pleasantness summary
	-> #trail, #chord, #samples, mean #slider_pleasantness, time bin (onset, offset)/chord

	*pupil samples_long
	-> pupil timestamp, world index^, eye_id, all 2D diameter related info

	*pupil summary
	-> #trail, #chord, #annotation_timestamp bin (on/offset), eye_id, #diameter sample, 
	   mean dilation, sd dilation

	*pupil vectors
	-> same as the pupil summary, but with dilation/trail stored as a vector



To check:
- if the annotation_timestamp is aligned with the pupil capture's one
	* noticed there might be a shift
	* may use the "world index^" to check [world index -> world cam sample/frame]?

- baseline needs to be set (should depend on the first few sec/practice trials if there are any)

